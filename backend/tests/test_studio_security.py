import base64
import hashlib
import os
import secrets

import pytest
import requests


# Studio auth/consent/authorization regression coverage
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


def _b64_bytes(size: int) -> str:
    return base64.b64encode(secrets.token_bytes(size)).decode()


def _vault_payload() -> dict:
    return {
        "salt": _b64_bytes(16),
        "verifier": {"algorithm": "AES-GCM", "iv": _b64_bytes(12), "ciphertext": _b64_bytes(24)},
        "iterations": 310000,
    }


def _memory_payload(title: str, privacy: str = "shareable", category: str = "AI Context") -> dict:
    return {
        "title": title,
        "category": category,
        "privacy": privacy,
        "encrypted_payload": {"algorithm": "AES-GCM", "iv": _b64_bytes(12), "ciphertext": _b64_bytes(24)},
    }


def _task_digest(task: str) -> str:
    return hashlib.sha256(task.encode()).hexdigest()


@pytest.fixture(scope="session")
def api_base_url() -> str:
    if not BASE_URL:
        pytest.fail("REACT_APP_BACKEND_URL is required in environment")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def api_client() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def _create_owner(api_client: requests.Session, api_base_url: str) -> dict:
    credential = secrets.token_hex(32)
    auth = api_client.post(f"{api_base_url}/api/auth/demo", json={"credential": credential})
    assert auth.status_code == 200
    token = auth.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    setup = api_client.post(f"{api_base_url}/api/vault/setup", json=_vault_payload(), headers=headers)
    assert setup.status_code == 200

    return {"headers": headers, "user": auth.json()["user"], "token": token}


def _create_connected_agent(api_client, api_base_url, headers, name="TEST Studio Agent"):
    agent = api_client.post(
        f"{api_base_url}/api/agents",
        json={"name": name, "developer": "QA", "kind": "personal"},
        headers=headers,
    )
    assert agent.status_code == 201
    return agent.json()


def _create_memory(api_client, api_base_url, headers, title, privacy="shareable", category="AI Context"):
    memory = api_client.post(
        f"{api_base_url}/api/memories",
        json=_memory_payload(title=title, privacy=privacy, category=category),
        headers=headers,
    )
    assert memory.status_code == 201
    return memory.json()


def _grant_memory(api_client, api_base_url, headers, agent_id, memory_id):
    grant = api_client.post(
        f"{api_base_url}/api/permissions",
        json={"agent_id": agent_id, "target_type": "memory", "target": memory_id},
        headers=headers,
    )
    assert grant.status_code == 201
    return grant.json()


def test_studio_owner_session_required_for_config_prepare_execute_and_runs(api_client: requests.Session, api_base_url: str):
    task = "quick test"
    payload_prepare = {"agent_id": "agent_x", "memory_ids": [], "task_digest": _task_digest(task)}
    payload_execute = {"consent_token": "x" * 40, "approved": True, "task": task, "contexts": []}

    assert api_client.get(f"{api_base_url}/api/studio/config").status_code == 401
    assert api_client.post(f"{api_base_url}/api/studio/prepare", json=payload_prepare).status_code == 401
    execute = api_client.post(f"{api_base_url}/api/studio/execute", json=payload_execute)
    assert execute.status_code == 401
    assert api_client.get(f"{api_base_url}/api/studio/runs").status_code == 401


def test_studio_api_key_not_accepted_for_owner_endpoints(api_client: requests.Session, api_base_url: str):
    owner = _create_owner(api_client, api_base_url)
    agent = _create_connected_agent(api_client, api_base_url, owner["headers"], name="TEST API Key Rejection")

    key_resp = api_client.post(
        f"{api_base_url}/api/keys",
        json={"name": "TEST Studio Key", "agent_id": agent["id"], "can_write": False},
        headers=owner["headers"],
    )
    assert key_resp.status_code == 201
    key = key_resp.json()["key"]
    key_headers = {"Authorization": f"Bearer {key}"}

    denied = api_client.get(f"{api_base_url}/api/studio/config", headers=key_headers)
    assert denied.status_code == 401


def test_prepare_returns_ciphertext_not_plaintext_and_consistent_task_digest(api_client: requests.Session, api_base_url: str):
    owner = _create_owner(api_client, api_base_url)
    agent = _create_connected_agent(api_client, api_base_url, owner["headers"], name="TEST Prepare Cipher")
    memory = _create_memory(api_client, api_base_url, owner["headers"], "TEST Cipher Memory")
    _grant_memory(api_client, api_base_url, owner["headers"], agent["id"], memory["id"])

    task = "Summarize preferences in one sentence."
    prepare = api_client.post(
        f"{api_base_url}/api/studio/prepare",
        json={"agent_id": agent["id"], "memory_ids": [memory["id"]], "task_digest": _task_digest(task)},
        headers=owner["headers"],
    )
    assert prepare.status_code == 200
    body = prepare.json()
    assert isinstance(body["consent_token"], str) and len(body["consent_token"]) >= 32
    assert body["provider"] == "OpenAI via Emergent"
    assert body["memories"][0]["id"] == memory["id"]
    assert "encrypted_payload" in body["memories"][0]
    assert "content" not in body["memories"][0]


def test_private_memory_rejected_by_prepare_even_with_category_permission(api_client: requests.Session, api_base_url: str):
    owner = _create_owner(api_client, api_base_url)
    agent = _create_connected_agent(api_client, api_base_url, owner["headers"], name="TEST Private Denied")
    private_memory = _create_memory(api_client, api_base_url, owner["headers"], "TEST Private Studio", privacy="private", category="AI Context")

    category_grant = api_client.post(
        f"{api_base_url}/api/permissions",
        json={"agent_id": agent["id"], "target_type": "category", "target": "AI Context"},
        headers=owner["headers"],
    )
    assert category_grant.status_code == 201

    task = "Use context"
    denied = api_client.post(
        f"{api_base_url}/api/studio/prepare",
        json={"agent_id": agent["id"], "memory_ids": [private_memory["id"]], "task_digest": _task_digest(task)},
        headers=owner["headers"],
    )
    assert denied.status_code == 403


def test_disconnected_agent_denied_in_prepare(api_client: requests.Session, api_base_url: str):
    owner = _create_owner(api_client, api_base_url)
    agent = _create_connected_agent(api_client, api_base_url, owner["headers"], name="TEST Disconnected")
    memory = _create_memory(api_client, api_base_url, owner["headers"], "TEST Disconnected Memory")
    _grant_memory(api_client, api_base_url, owner["headers"], agent["id"], memory["id"])

    disconnect = api_client.patch(
        f"{api_base_url}/api/agents/{agent['id']}",
        json={"status": "disconnected"},
        headers=owner["headers"],
    )
    assert disconnect.status_code == 200

    denied = api_client.post(
        f"{api_base_url}/api/studio/prepare",
        json={"agent_id": agent["id"], "memory_ids": [memory["id"]], "task_digest": _task_digest("Any")},
        headers=owner["headers"],
    )
    assert denied.status_code == 403


def test_cross_user_execute_with_foreign_token_denied(api_client: requests.Session, api_base_url: str):
    owner_a = _create_owner(api_client, api_base_url)
    owner_b = _create_owner(api_client, api_base_url)

    agent_a = _create_connected_agent(api_client, api_base_url, owner_a["headers"], name="TEST OwnerA")
    memory_a = _create_memory(api_client, api_base_url, owner_a["headers"], "TEST A Memory")
    _grant_memory(api_client, api_base_url, owner_a["headers"], agent_a["id"], memory_a["id"])

    task = "Short task"
    prepared = api_client.post(
        f"{api_base_url}/api/studio/prepare",
        json={"agent_id": agent_a["id"], "memory_ids": [memory_a["id"]], "task_digest": _task_digest(task)},
        headers=owner_a["headers"],
    )
    assert prepared.status_code == 200

    denied = api_client.post(
        f"{api_base_url}/api/studio/execute",
        json={
            "consent_token": prepared.json()["consent_token"],
            "approved": True,
            "task": task,
            "contexts": [{"memory_id": memory_a["id"], "content": "x"}],
        },
        headers=owner_b["headers"],
    )
    assert denied.status_code == 409


def test_revoke_after_prepare_blocks_execute_before_dispatch(api_client: requests.Session, api_base_url: str):
    owner = _create_owner(api_client, api_base_url)
    agent = _create_connected_agent(api_client, api_base_url, owner["headers"], name="TEST Revoke Before Execute")
    memory = _create_memory(api_client, api_base_url, owner["headers"], "TEST Revoke Memory")
    permission = _grant_memory(api_client, api_base_url, owner["headers"], agent["id"], memory["id"])

    task = "Explain"
    prepared = api_client.post(
        f"{api_base_url}/api/studio/prepare",
        json={"agent_id": agent["id"], "memory_ids": [memory["id"]], "task_digest": _task_digest(task)},
        headers=owner["headers"],
    )
    assert prepared.status_code == 200

    revoked = api_client.delete(f"{api_base_url}/api/permissions/{permission['id']}", headers=owner["headers"])
    assert revoked.status_code == 200

    denied = api_client.post(
        f"{api_base_url}/api/studio/execute",
        json={
            "consent_token": prepared.json()["consent_token"],
            "approved": True,
            "task": task,
            "contexts": [{"memory_id": memory["id"], "content": "local decrypted context"}],
        },
        headers=owner["headers"],
    )
    assert denied.status_code == 403


def test_memory_edit_after_prepare_invalidates_execute(api_client: requests.Session, api_base_url: str):
    owner = _create_owner(api_client, api_base_url)
    agent = _create_connected_agent(api_client, api_base_url, owner["headers"], name="TEST Snapshot Invalidation")
    memory = _create_memory(api_client, api_base_url, owner["headers"], "TEST Snapshot")
    _grant_memory(api_client, api_base_url, owner["headers"], agent["id"], memory["id"])

    task = "Task"
    prepared = api_client.post(
        f"{api_base_url}/api/studio/prepare",
        json={"agent_id": agent["id"], "memory_ids": [memory["id"]], "task_digest": _task_digest(task)},
        headers=owner["headers"],
    )
    assert prepared.status_code == 200

    changed = api_client.patch(
        f"{api_base_url}/api/memories/{memory['id']}",
        json=_memory_payload("TEST Snapshot Updated", privacy="shareable", category="AI Context"),
        headers=owner["headers"],
    )
    assert changed.status_code == 200

    denied = api_client.post(
        f"{api_base_url}/api/studio/execute",
        json={
            "consent_token": prepared.json()["consent_token"],
            "approved": True,
            "task": task,
            "contexts": [{"memory_id": memory["id"], "content": "x"}],
        },
        headers=owner["headers"],
    )
    assert denied.status_code == 409


def test_execute_rejects_changed_task_or_context_set(api_client: requests.Session, api_base_url: str):
    owner = _create_owner(api_client, api_base_url)
    agent = _create_connected_agent(api_client, api_base_url, owner["headers"], name="TEST Task/Context Integrity")
    memory = _create_memory(api_client, api_base_url, owner["headers"], "TEST Integrity Memory")
    _grant_memory(api_client, api_base_url, owner["headers"], agent["id"], memory["id"])

    task = "Original task"
    prepared = api_client.post(
        f"{api_base_url}/api/studio/prepare",
        json={"agent_id": agent["id"], "memory_ids": [memory["id"]], "task_digest": _task_digest(task)},
        headers=owner["headers"],
    )
    assert prepared.status_code == 200

    changed_task = api_client.post(
        f"{api_base_url}/api/studio/execute",
        json={
            "consent_token": prepared.json()["consent_token"],
            "approved": True,
            "task": "Mutated task",
            "contexts": [{"memory_id": memory["id"], "content": "x"}],
        },
        headers=owner["headers"],
    )
    assert changed_task.status_code == 409

    prepared2 = api_client.post(
        f"{api_base_url}/api/studio/prepare",
        json={"agent_id": agent["id"], "memory_ids": [memory["id"]], "task_digest": _task_digest(task)},
        headers=owner["headers"],
    )
    assert prepared2.status_code == 200

    changed_context_set = api_client.post(
        f"{api_base_url}/api/studio/execute",
        json={
            "consent_token": prepared2.json()["consent_token"],
            "approved": True,
            "task": task,
            "contexts": [],
        },
        headers=owner["headers"],
    )
    assert changed_context_set.status_code == 409


def test_execute_rejects_approved_false_or_missing_and_sanitizes_422(api_client: requests.Session, api_base_url: str):
    owner = _create_owner(api_client, api_base_url)

    bad_false = api_client.post(
        f"{api_base_url}/api/studio/execute",
        json={"consent_token": "x" * 40, "approved": False, "task": "secret should not echo", "contexts": []},
        headers=owner["headers"],
    )
    assert bad_false.status_code == 422
    detail_false = bad_false.json().get("detail", "")
    assert isinstance(detail_false, str)
    assert "secret should not echo" not in detail_false

    bad_missing = api_client.post(
        f"{api_base_url}/api/studio/execute",
        json={"consent_token": "x" * 40, "task": "top_secret_context", "contexts": []},
        headers=owner["headers"],
    )
    assert bad_missing.status_code == 422
    detail_missing = bad_missing.json().get("detail", "")
    assert "top_secret_context" not in detail_missing
    assert "Invalid task request" in detail_missing

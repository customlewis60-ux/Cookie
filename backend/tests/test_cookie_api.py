import base64
import os
import secrets

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


def _b64_bytes(size: int) -> str:
    return base64.b64encode(secrets.token_bytes(size)).decode()


def _vault_payload() -> dict:
    # Vault setup validation payload (salt + AES-GCM envelope shape)
    return {
        "salt": _b64_bytes(16),
        "verifier": {
            "algorithm": "AES-GCM",
            "iv": _b64_bytes(12),
            "ciphertext": _b64_bytes(24),
        },
        "iterations": 310000,
    }


def _memory_payload(title: str, category: str = "Personal", privacy: str = "private") -> dict:
    # Memory CRUD payload with encrypted envelope fields
    return {
        "title": title,
        "category": category,
        "privacy": privacy,
        "encrypted_payload": {
            "algorithm": "AES-GCM",
            "iv": _b64_bytes(12),
            "ciphertext": _b64_bytes(24),
        },
    }


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


@pytest.fixture(scope="session")
def auth_context(api_client: requests.Session, api_base_url: str) -> dict:
    # Demo auth + owner session setup
    credential = secrets.token_hex(32)
    response = api_client.post(f"{api_base_url}/api/auth/demo", json={"credential": credential})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data and isinstance(data["token"], str) and len(data["token"]) > 10
    assert "user" in data and data["user"]["mode"] == "demo"
    headers = {"Authorization": f"Bearer {data['token']}"}
    return {"headers": headers, "user": data["user"], "token": data["token"]}


def test_health(api_client: requests.Session, api_base_url: str):
    response = api_client.get(f"{api_base_url}/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["product"] == "COOKIE"


def test_auth_me_returns_demo_identity(api_client: requests.Session, api_base_url: str, auth_context: dict):
    response = api_client.get(f"{api_base_url}/api/auth/me", headers=auth_context["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == auth_context["user"]["id"]
    assert body["mode"] == "demo"
    assert "credential_hash" not in body


def test_vault_setup_then_second_setup_conflicts(api_client: requests.Session, api_base_url: str, auth_context: dict):
    first = api_client.post(f"{api_base_url}/api/vault/setup", json=_vault_payload(), headers=auth_context["headers"])
    assert first.status_code == 200
    assert first.json()["ok"] is True

    second = api_client.post(f"{api_base_url}/api/vault/setup", json=_vault_payload(), headers=auth_context["headers"])
    assert second.status_code == 409
    assert "already" in second.json()["detail"].lower()


def test_memory_create_get_patch_and_delete(api_client: requests.Session, api_base_url: str, auth_context: dict):
    create_payload = _memory_payload("TEST_API Memory", category="Work", privacy="shareable")
    created = api_client.post(f"{api_base_url}/api/memories", json=create_payload, headers=auth_context["headers"])
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["title"] == "TEST_API Memory"
    assert created_body["category"] == "Work"
    assert created_body["privacy"] == "shareable"
    memory_id = created_body["id"]

    fetched = api_client.get(f"{api_base_url}/api/memories/{memory_id}", headers=auth_context["headers"])
    assert fetched.status_code == 200
    fetched_body = fetched.json()
    assert fetched_body["id"] == memory_id
    assert fetched_body["encrypted_payload"]["algorithm"] == "AES-GCM"

    update_payload = _memory_payload("TEST_API Memory Updated", category="Projects", privacy="private")
    updated = api_client.patch(f"{api_base_url}/api/memories/{memory_id}", json=update_payload, headers=auth_context["headers"])
    assert updated.status_code == 200
    updated_body = updated.json()
    assert updated_body["title"] == "TEST_API Memory Updated"
    assert updated_body["privacy"] == "private"

    verify = api_client.get(f"{api_base_url}/api/memories/{memory_id}", headers=auth_context["headers"])
    assert verify.status_code == 200
    assert verify.json()["category"] == "Projects"

    deleted = api_client.delete(f"{api_base_url}/api/memories/{memory_id}", headers=auth_context["headers"])
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True

    missing = api_client.get(f"{api_base_url}/api/memories/{memory_id}", headers=auth_context["headers"])
    assert missing.status_code == 404


def test_private_memory_cannot_be_granted_to_agent(api_client: requests.Session, api_base_url: str, auth_context: dict):
    memory = api_client.post(
        f"{api_base_url}/api/memories",
        json=_memory_payload("TEST_Private Only", category="Personal", privacy="private"),
        headers=auth_context["headers"],
    )
    assert memory.status_code == 201
    memory_id = memory.json()["id"]

    agent = api_client.post(
        f"{api_base_url}/api/agents",
        json={"name": "TEST Agent", "developer": "QA", "kind": "custom"},
        headers=auth_context["headers"],
    )
    assert agent.status_code == 201
    agent_id = agent.json()["id"]

    grant = api_client.post(
        f"{api_base_url}/api/permissions",
        json={"agent_id": agent_id, "target_type": "memory", "target": memory_id},
        headers=auth_context["headers"],
    )
    assert grant.status_code == 403
    assert "private" in grant.json()["detail"].lower()


def test_agent_key_and_read_authorization(api_client: requests.Session, api_base_url: str, auth_context: dict):
    # Agent, permissions, API key and developer endpoint behavior
    shareable = api_client.post(
        f"{api_base_url}/api/memories",
        json=_memory_payload("TEST_Shareable", category="Knowledge", privacy="shareable"),
        headers=auth_context["headers"],
    )
    assert shareable.status_code == 201
    memory_id = shareable.json()["id"]

    agent = api_client.post(
        f"{api_base_url}/api/agents",
        json={"name": "TEST Research", "developer": "QA", "kind": "research"},
        headers=auth_context["headers"],
    )
    assert agent.status_code == 201
    agent_id = agent.json()["id"]

    permission = api_client.post(
        f"{api_base_url}/api/permissions",
        json={"agent_id": agent_id, "target_type": "memory", "target": memory_id},
        headers=auth_context["headers"],
    )
    assert permission.status_code == 201
    assert permission.json()["agent_id"] == agent_id

    key_resp = api_client.post(
        f"{api_base_url}/api/keys",
        json={"name": "TEST Key", "agent_id": agent_id, "can_write": False},
        headers=auth_context["headers"],
    )
    assert key_resp.status_code == 201
    key_body = key_resp.json()
    assert key_body["key"].startswith("ck_demo_")
    assert "key_hash" not in key_body["record"]

    owner_keys = api_client.get(f"{api_base_url}/api/keys", headers=auth_context["headers"])
    assert owner_keys.status_code == 200
    listed = owner_keys.json()
    assert isinstance(listed, list)
    assert all("key_hash" not in k for k in listed)

    agent_headers = {"Authorization": f"Bearer {key_body['key']}"}
    read_list = api_client.get(f"{api_base_url}/api/v1/memory", headers=agent_headers)
    assert read_list.status_code == 200
    returned_ids = [m["id"] for m in read_list.json()]
    assert memory_id in returned_ids

    read_single = api_client.get(f"{api_base_url}/api/v1/memory/{memory_id}", headers=agent_headers)
    assert read_single.status_code == 200
    assert read_single.json()["id"] == memory_id


def test_disconnect_agent_revokes_permissions_and_blocks_key(api_client: requests.Session, api_base_url: str, auth_context: dict):
    memory = api_client.post(
        f"{api_base_url}/api/memories",
        json=_memory_payload("TEST_Disconnect", category="Projects", privacy="shareable"),
        headers=auth_context["headers"],
    )
    assert memory.status_code == 201
    memory_id = memory.json()["id"]

    agent = api_client.post(
        f"{api_base_url}/api/agents",
        json={"name": "TEST Disconnect Agent", "developer": "QA", "kind": "custom"},
        headers=auth_context["headers"],
    )
    assert agent.status_code == 201
    agent_id = agent.json()["id"]

    grant = api_client.post(
        f"{api_base_url}/api/permissions",
        json={"agent_id": agent_id, "target_type": "memory", "target": memory_id},
        headers=auth_context["headers"],
    )
    assert grant.status_code == 201

    key_resp = api_client.post(
        f"{api_base_url}/api/keys",
        json={"name": "TEST Disconnect Key", "agent_id": agent_id, "can_write": False},
        headers=auth_context["headers"],
    )
    assert key_resp.status_code == 201
    key_value = key_resp.json()["key"]
    agent_headers = {"Authorization": f"Bearer {key_value}"}

    before = api_client.get(f"{api_base_url}/api/v1/memory", headers=agent_headers)
    assert before.status_code == 200

    disconnect = api_client.patch(
        f"{api_base_url}/api/agents/{agent_id}",
        json={"status": "disconnected"},
        headers=auth_context["headers"],
    )
    assert disconnect.status_code == 200
    assert disconnect.json()["status"] == "disconnected"

    after = api_client.get(f"{api_base_url}/api/v1/memory", headers=agent_headers)
    assert after.status_code == 401
    assert "disconnected" in after.json()["detail"].lower()


def test_no_auth_denied_for_owner_memory_crud(api_client: requests.Session, api_base_url: str):
    create = api_client.post(f"{api_base_url}/api/memories", json=_memory_payload("TEST_NoAuth"))
    assert create.status_code == 401
    assert "session" in create.json()["detail"].lower()

    dashboard = api_client.get(f"{api_base_url}/api/dashboard")
    assert dashboard.status_code == 401
    assert "session" in dashboard.json()["detail"].lower()


def test_key_rotate_invalidates_old_key(api_client: requests.Session, api_base_url: str, auth_context: dict):
    memory = api_client.post(
        f"{api_base_url}/api/memories",
        json=_memory_payload("TEST_Rotate", category="Trading", privacy="shareable"),
        headers=auth_context["headers"],
    )
    assert memory.status_code == 201
    memory_id = memory.json()["id"]

    agent = api_client.post(
        f"{api_base_url}/api/agents",
        json={"name": "TEST Rotate Agent", "developer": "QA", "kind": "custom"},
        headers=auth_context["headers"],
    )
    assert agent.status_code == 201
    agent_id = agent.json()["id"]

    grant = api_client.post(
        f"{api_base_url}/api/permissions",
        json={"agent_id": agent_id, "target_type": "memory", "target": memory_id},
        headers=auth_context["headers"],
    )
    assert grant.status_code == 201

    key_resp = api_client.post(
        f"{api_base_url}/api/keys",
        json={"name": "TEST Rotate Key", "agent_id": agent_id, "can_write": False},
        headers=auth_context["headers"],
    )
    assert key_resp.status_code == 201
    old_key = key_resp.json()["key"]
    key_id = key_resp.json()["record"]["id"]

    rotated = api_client.post(f"{api_base_url}/api/keys/{key_id}/rotate", headers=auth_context["headers"])
    assert rotated.status_code == 200
    new_key = rotated.json()["key"]
    assert new_key != old_key

    old_use = api_client.get(f"{api_base_url}/api/v1/memory", headers={"Authorization": f"Bearer {old_key}"})
    assert old_use.status_code == 401

    new_use = api_client.get(f"{api_base_url}/api/v1/memory", headers={"Authorization": f"Bearer {new_key}"})
    assert new_use.status_code == 200


def test_write_requires_write_key_and_category_permission(api_client: requests.Session, api_base_url: str, auth_context: dict):
    agent = api_client.post(
        f"{api_base_url}/api/agents",
        json={"name": "TEST Write Agent", "developer": "QA", "kind": "custom"},
        headers=auth_context["headers"],
    )
    assert agent.status_code == 201
    agent_id = agent.json()["id"]

    key_resp = api_client.post(
        f"{api_base_url}/api/keys",
        json={"name": "TEST Write Key", "agent_id": agent_id, "can_write": True},
        headers=auth_context["headers"],
    )
    assert key_resp.status_code == 201
    api_key = key_resp.json()["key"]
    key_headers = {"Authorization": f"Bearer {api_key}"}

    denied = api_client.post(
        f"{api_base_url}/api/v1/memory",
        json=_memory_payload("TEST_Write_Denied", category="Preferences", privacy="shareable"),
        headers=key_headers,
    )
    assert denied.status_code == 403
    assert "category permission" in denied.json()["detail"].lower()

    grant = api_client.post(
        f"{api_base_url}/api/permissions",
        json={"agent_id": agent_id, "target_type": "category", "target": "Preferences"},
        headers=auth_context["headers"],
    )
    assert grant.status_code == 201

    allowed = api_client.post(
        f"{api_base_url}/api/v1/memory",
        json=_memory_payload("TEST_Write_Allowed", category="Preferences", privacy="shareable"),
        headers=key_headers,
    )
    assert allowed.status_code == 201
    assert allowed.json()["title"] == "TEST_Write_Allowed"


def test_cross_user_memory_access_is_denied(api_client: requests.Session, api_base_url: str, auth_context: dict):
    owner2_credential = secrets.token_hex(32)
    owner2 = api_client.post(f"{api_base_url}/api/auth/demo", json={"credential": owner2_credential})
    assert owner2.status_code == 200
    owner2_headers = {"Authorization": f"Bearer {owner2.json()['token']}"}

    vault = api_client.post(f"{api_base_url}/api/vault/setup", json=_vault_payload(), headers=owner2_headers)
    assert vault.status_code == 200

    owner2_memory = api_client.post(
        f"{api_base_url}/api/memories",
        json=_memory_payload("TEST_Owner2", category="AI Context", privacy="shareable"),
        headers=owner2_headers,
    )
    assert owner2_memory.status_code == 201
    owner2_memory_id = owner2_memory.json()["id"]

    owner1_agent = api_client.post(
        f"{api_base_url}/api/agents",
        json={"name": "TEST Owner1 Reader", "developer": "QA", "kind": "custom"},
        headers=auth_context["headers"],
    )
    assert owner1_agent.status_code == 201
    agent_id = owner1_agent.json()["id"]

    owner1_key = api_client.post(
        f"{api_base_url}/api/keys",
        json={"name": "TEST Owner1 Key", "agent_id": agent_id, "can_write": False},
        headers=auth_context["headers"],
    )
    assert owner1_key.status_code == 201
    owner1_key_value = owner1_key.json()["key"]

    denied = api_client.get(
        f"{api_base_url}/api/v1/memory/{owner2_memory_id}",
        headers={"Authorization": f"Bearer {owner1_key_value}"},
    )
    assert denied.status_code == 403
    assert "not authorized" in denied.json()["detail"].lower()

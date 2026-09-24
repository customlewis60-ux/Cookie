import asyncio
import contextlib
import json
import time
from fastapi import HTTPException
from core import db, now, log
from studio_guard import assert_live, release_slot
from studio_ai import produce


def sse(event, data):
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


async def run_stream(request, user, agent, preparation, payload, receipt, authorization, timeout):
    queue = asyncio.Queue(maxsize=64)
    worker = None
    started = time.monotonic()
    status, error_code, usage = 'cancelled', None, {}
    run_id = receipt['id']
    received_text = False
    try:
        # Recheck immediately at the dispatch boundary, not merely at preparation.
        _, memories = await assert_live(user, agent['id'], preparation['snapshots'], authorization, run_id)
        by_id = {m['id']: m for m in memories}
        contexts = [{'memory_id': c.memory_id, 'title': by_id[c.memory_id]['title'], 'content': c.content} for c in payload.contexts]
        await log(user['id'], 'consent_granted', f'{agent["name"]} · {len(memories)} memories · one task', agent['id'])
        for memory in memories:
            await log(user['id'], 'memory_released_to_agent', memory['title'], agent['id'], memory['id'])
            await db.memories.update_one({'id': memory['id'], 'user_id': user['id']}, {'$set': {'last_accessed': now()}})
        await db.agents.update_one({'id': agent['id'], 'user_id': user['id']}, {'$set': {'last_activity': now()}})
        # Logging requires awaits; recheck once more immediately before scheduling
        # the provider call so a revocation during those writes cannot slip through.
        await assert_live(user, agent['id'], preparation['snapshots'], authorization, run_id)
        # Every task receives a fresh client/session, including no-memory runs.
        worker = asyncio.create_task(produce(queue, run_id, agent, payload.task, contexts, receipt['model']))
        yield sse('started', {'run_id': run_id, 'agent_name': agent['name'], 'provider': 'OpenAI via Emergent', 'model': receipt['model'], 'memory_ids': list(preparation['snapshots']), 'memory_count': len(memories)})
        last_check, last_heartbeat = time.monotonic(), time.monotonic()
        while True:
            if time.monotonic() - started > timeout:
                status, error_code = 'failed', 'timeout'
                yield sse('error', {'code': error_code, 'message': 'The AI task timed out. Review and approve another request to retry.'})
                break
            if await request.is_disconnected():
                status = 'cancelled'
                break
            if time.monotonic() - last_check >= 0.75:
                await assert_live(user, agent['id'], preparation['snapshots'], authorization, run_id)
                last_check = time.monotonic()
            try:
                event, details = await asyncio.wait_for(queue.get(), timeout=0.3)
            except asyncio.TimeoutError:
                if time.monotonic() - last_heartbeat > 8:
                    yield ': keepalive\n\n'
                    last_heartbeat = time.monotonic()
                continue
            if event == 'delta':
                received_text = received_text or bool(details['text'].strip())
                yield sse('delta', details)
            elif event == 'done':
                await assert_live(user, agent['id'], preparation['snapshots'], authorization, run_id)
                if not received_text:
                    status, error_code = 'failed', 'empty_response'
                    yield sse('error', {'code': error_code, 'message': 'The model returned no text. Review and approve a new task to retry.'})
                else:
                    status = 'completed'
                    usage = {k: details[k] for k in ['input_tokens', 'output_tokens']}
                    yield sse('done', {'run_id': run_id, 'status': status, 'duration_ms': round((time.monotonic() - started) * 1000), **details})
                break
            else:
                status, error_code = 'failed', details['code']
                yield sse('error', details)
                break
    except HTTPException as exc:
        status = 'cancelled' if exc.status_code in (401, 409) and 'stopped' in exc.detail else 'denied'
        error_code = 'access_changed'
        yield sse('error', {'code': error_code, 'message': exc.detail + ' Previously sent context cannot be recalled.'})
    except asyncio.CancelledError:
        status = 'cancelled'
        raise
    except Exception:
        status, error_code = 'failed', 'runtime_error'
        yield sse('error', {'code': error_code, 'message': 'This task could not be completed. No result has been saved.'})
    finally:
        if worker:
            worker.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await worker
        async def finalize():
            await db.studio_runs.update_one({'id': run_id, 'user_id': user['id']}, {'$set': {'status': status, 'error_code': error_code, 'finished_at': now(), 'duration_ms': round((time.monotonic() - started) * 1000), **usage}})
            await release_slot(user['id'], run_id)
            await log(user['id'], 'agent_task_' + status, f'{agent["name"]} · {len(preparation["snapshots"])} memories · {receipt["model"]}', agent['id'])
        await asyncio.shield(finalize())
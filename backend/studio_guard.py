"""Owner consent, live authorization, metadata-only receipts and bounded usage."""
import json
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from core import db, digest, now, owned, permitted, log


def utcnow():
    return datetime.now(timezone.utc)


def payload_version(memory):
    return digest(json.dumps(memory['encrypted_payload'], sort_keys=True, separators=(',', ':')))


async def authorize(user, agent_id, memory_ids, snapshots=None):
    agent = await owned('agents', agent_id, user)
    if agent['status'] != 'connected':
        raise HTTPException(403, 'This agent is disconnected. Connect it and review access again.')
    memories = []
    for memory_id in memory_ids:
        memory = await owned('memories', memory_id, user)
        if not await permitted(user['id'], agent_id, memory):
            raise HTTPException(403, 'Memory access has been revoked or is not authorized. Review permissions before running this task.')
        if snapshots is not None:
            snapshot = snapshots.get(memory_id)
            if not snapshot or snapshot['updated_at'] != memory['updated_at'] or snapshot['version'] != payload_version(memory):
                raise HTTPException(409, 'A selected memory changed. Unlock and review the current version before sending.')
        memories.append(memory)
    return agent, memories


async def record_denial(user, agent_id):
    # Do not record the submitted task, content, token, or error details.
    await log(user['id'], 'agent_access_denied', 'Agent Studio · context access denied', agent_id)


async def acquire_slot(user_id, run_id, timeout):
    await db.studio_slots.delete_many({'user_id': user_id, 'expires_at': {'$lte': utcnow()}})
    try:
        await db.studio_slots.insert_one({'user_id': user_id, 'run_id': run_id, 'expires_at': utcnow() + timedelta(seconds=timeout + 30)})
    except DuplicateKeyError:
        raise HTTPException(409, 'A task is already running in your workspace. Stop it or wait for it to finish.')


async def release_slot(user_id, run_id):
    await db.studio_slots.delete_one({'user_id': user_id, 'run_id': run_id})


async def check_budget(user_id, hourly_limit, daily_limit):
    current = utcnow()
    buckets = [(f'user:{user_id}:{current.strftime("%Y%m%d%H")}', hourly_limit),
               (f'app:{current.strftime("%Y%m%d")}', daily_limit)]
    reserved = []
    for bucket, limit in buckets:
        try:
            await db.studio_budgets.update_one({'id': bucket}, {'$setOnInsert': {'count': 0, 'expires_at': current + timedelta(days=2)}}, upsert=True)
        except DuplicateKeyError:
            pass  # Another workspace initialized the shared daily bucket.
        record = await db.studio_budgets.find_one_and_update(
            {'id': bucket, 'count': {'$lt': limit}}, {'$inc': {'count': 1}},
            return_document=ReturnDocument.AFTER, projection={'_id': 0})
        if not record:
            # A rejected attempt does not consume or inflate either allowance.
            for prior in reserved:
                await db.studio_budgets.update_one({'id': prior, 'count': {'$gt': 0}}, {'$inc': {'count': -1}})
            raise HTTPException(429, 'The AI task allowance for this period has been reached. Please try again later.')
        reserved.append(bucket)


async def assert_live(user, agent_id, snapshots, authorization, run_id):
    session = await db.sessions.find_one({'user_id': user['id'], 'token_hash': digest(authorization.removeprefix('Bearer ')), 'expires_at': {'$gt': now()}}, {'_id': 0})
    if not session:
        raise HTTPException(401, 'Your session ended. This task has been stopped.')
    receipt = await db.studio_runs.find_one({'id': run_id, 'user_id': user['id']}, {'_id': 0, 'cancel_requested': 1})
    if not receipt or receipt.get('cancel_requested'):
        raise HTTPException(409, 'This task was stopped.')
    return await authorize(user, agent_id, list(snapshots), snapshots)
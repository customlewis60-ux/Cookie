import secrets
import time
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from core import db, owner, owned, uid, now, digest, permitted, log
from models import KeyInput, MemoryInput, MemoryResponse

router = APIRouter()

@router.get('/keys')
async def keys(user=Depends(owner)):
    return await db.api_keys.find({'user_id': user['id']}, {'_id': 0, 'key_hash': 0}).sort('created_at', -1).to_list(200)

async def issue_key(data, user):
    agent = await owned('agents', data.agent_id, user)
    if agent['status'] != 'connected': raise HTTPException(409, 'Connect this agent first')
    raw = 'ck_demo_' + secrets.token_urlsafe(32)
    key = {**data.model_dump(), 'id': uid('key'), 'user_id': user['id'], 'key_hash': digest(raw), 'prefix': raw[:16], 'created_at': now(), 'revoked_at': None, 'last_used': None}
    await db.api_keys.insert_one(key.copy())
    await log(user['id'], 'key_created', data.name, data.agent_id)
    return {'key': raw, 'record': {k: v for k, v in key.items() if k != 'key_hash'}}

@router.post('/keys', status_code=201)
async def create_key(data: KeyInput, user=Depends(owner)): return await issue_key(data, user)

@router.delete('/keys/{key_id}')
async def revoke_key(key_id: str, user=Depends(owner)):
    key = await owned('api_keys', key_id, user)
    await db.api_keys.update_one({'id': key_id, 'user_id': user['id']}, {'$set': {'revoked_at': now()}})
    await log(user['id'], 'key_revoked', key['name'])
    return {'ok': True}

@router.post('/keys/{key_id}/rotate')
async def rotate_key(key_id: str, user=Depends(owner)):
    key = await owned('api_keys', key_id, user)
    if key['revoked_at']: raise HTTPException(409, 'This key is already revoked')
    replacement = await issue_key(KeyInput(name=key['name'], agent_id=key['agent_id'], can_write=key['can_write']), user)
    await db.api_keys.update_one({'id': key_id, 'user_id': user['id']}, {'$set': {'revoked_at': now()}})
    await log(user['id'], 'key_rotated', key['name'])
    return replacement

async def agent_auth(request: Request, authorization: str = Header(default='')):
    key = await db.api_keys.find_one({'key_hash': digest(authorization.removeprefix('Bearer '))}, {'_id': 0})
    if not authorization.startswith('Bearer ') or not key: raise HTTPException(401, 'Invalid API key')
    agent = await db.agents.find_one({'id': key['agent_id'], 'user_id': key['user_id'], 'status': 'connected'}, {'_id': 0})
    if key['revoked_at'] or not agent:
        await request_log(key, request, 401)
        raise HTTPException(401, 'API key revoked or agent disconnected')
    await db.api_keys.update_one({'id': key['id']}, {'$set': {'last_used': now()}})
    return key

async def request_log(key, request, status):
    await db.requests.insert_one({'id': uid('req'), 'user_id': key['user_id'], 'agent_id': key['agent_id'], 'method': request.method, 'path': request.url.path, 'status': status, 'timestamp': now()})

@router.get('/v1/memory', response_model=list[MemoryResponse])
async def read_memories(request: Request, category: str = None, key=Depends(agent_auth)):
    query = {'user_id': key['user_id']}
    if category: query['category'] = category
    memories = await db.memories.find(query, {'_id': 0}).to_list(2000)
    allowed = []
    for memory in memories:
        if await permitted(key['user_id'], key['agent_id'], memory):
            allowed.append(memory)
            await log(key['user_id'], 'memory_accessed', memory['title'], key['agent_id'], memory['id'])
            await db.memories.update_one({'id': memory['id']}, {'$set': {'last_accessed': now()}})
    await db.agents.update_one({'id': key['agent_id']}, {'$set': {'last_activity': now()}})
    await request_log(key, request, 200)
    return allowed

@router.get('/v1/memory/{memory_id}', response_model=MemoryResponse)
async def read_memory(memory_id: str, request: Request, key=Depends(agent_auth)):
    memory = await db.memories.find_one({'id': memory_id, 'user_id': key['user_id']}, {'_id': 0})
    if not memory or not await permitted(key['user_id'], key['agent_id'], memory):
        await request_log(key, request, 403)
        raise HTTPException(403, 'Memory access is not authorized')
    await log(key['user_id'], 'memory_accessed', memory['title'], key['agent_id'], memory_id)
    await db.memories.update_one({'id': memory_id}, {'$set': {'last_accessed': now()}})
    await db.agents.update_one({'id': key['agent_id']}, {'$set': {'last_activity': now()}})
    await request_log(key, request, 200)
    return memory

@router.post('/v1/memory', response_model=MemoryResponse, status_code=201)
async def write_memory(data: MemoryInput, request: Request, key=Depends(agent_auth)):
    category_grant = await db.permissions.find_one({'user_id': key['user_id'], 'agent_id': key['agent_id'], 'target_type': 'category', 'target': data.category, 'revoked_at': None})
    if not key['can_write'] or not category_grant:
        await request_log(key, request, 403)
        raise HTTPException(403, 'Writing requires a write-enabled key and an active category permission')
    memory = {**data.model_dump(), 'id': uid('mem'), 'user_id': key['user_id'], 'created_at': now(), 'updated_at': now(), 'last_accessed': None}
    await db.memories.insert_one(memory.copy())
    await log(key['user_id'], 'memory_created', data.title, key['agent_id'], memory['id'])
    await request_log(key, request, 201)
    return memory

@router.post('/v1/permissions/revoke')
async def self_revoke(request: Request, key=Depends(agent_auth)):
    await db.permissions.update_many({'user_id': key['user_id'], 'agent_id': key['agent_id'], 'revoked_at': None}, {'$set': {'revoked_at': now()}})
    await log(key['user_id'], 'permission_revoked', 'Agent relinquished all permissions', key['agent_id'])
    await request_log(key, request, 200)
    return {'ok': True}

@router.get('/developer/stats')
async def stats(user=Depends(owner)):
    q = {'user_id': user['id']}
    total = await db.requests.count_documents(q)
    reads = await db.requests.count_documents({**q, 'method': 'GET', 'status': 200})
    writes = await db.requests.count_documents({**q, 'method': 'POST', 'status': 201})
    errors = await db.requests.count_documents({**q, 'status': {'$gte': 400}})
    logs = await db.requests.find(q, {'_id': 0}).sort('timestamp', -1).to_list(50)
    active = len(await db.requests.distinct('agent_id', q))
    return {'total': total, 'reads': reads, 'writes': writes, 'active_agents': active, 'error_rate': round(errors / total * 100, 1) if total else 0, 'logs': logs}
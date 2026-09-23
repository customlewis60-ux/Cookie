from fastapi import APIRouter, Depends, HTTPException, Header
from core import db, now, uid, digest, owner, owned, log, new_session, AGENTS, CATEGORIES
from models import DemoInput, VaultInput, MemoryInput, MemoryResponse, AgentInput, AgentUpdate, PermissionInput, ImportInput
from pymongo.errors import DuplicateKeyError
import secrets

router = APIRouter()

@router.post('/auth/demo')
async def demo(data: DemoInput):
    h = digest(data.credential)
    user = await db.users.find_one({'credential_hash': h}, {'_id': 0})
    if not user:
        user = {'id': uid('cookie'), 'wallet_address': '0x' + secrets.token_hex(20), 'credential_hash': h, 'created_at': now(), 'mode': 'demo', 'vault': None}
        try: await db.users.insert_one(user.copy())
        except DuplicateKeyError: user = await db.users.find_one({'credential_hash': h}, {'_id': 0})
    token = await new_session(user['id'])
    return {'token': token, 'user': {k: v for k, v in user.items() if k not in ['credential_hash', '_id']}}

@router.get('/auth/me')
async def me(user=Depends(owner)): return user

@router.post('/auth/logout')
async def logout(user=Depends(owner), authorization: str = Header()):
    await db.sessions.delete_one({'token_hash': digest(authorization.removeprefix('Bearer '))})
    return {'ok': True}

@router.post('/vault/setup')
async def setup(data: VaultInput, user=Depends(owner)):
    result = await db.users.update_one({'id': user['id'], 'vault': None}, {'$set': {'vault': data.model_dump()}})
    if not result.modified_count: raise HTTPException(409, 'This vault is already initialized')
    await log(user['id'], 'vault_created', 'Encrypted vault created')
    return {'ok': True}

@router.get('/dashboard')
async def dashboard(user=Depends(owner)):
    q = {'user_id': user['id']}
    memories = await db.memories.find(q, {'_id': 0, 'encrypted_payload': 0}).sort('created_at', -1).to_list(2000)
    agents = await db.agents.find(q, {'_id': 0}).to_list(200)
    permissions = await db.permissions.find({**q, 'revoked_at': None}, {'_id': 0}).to_list(5000)
    activity = await db.activity.find(q, {'_id': 0}).sort('timestamp', -1).to_list(200)
    for memory in memories:
        memory['agent_ids'] = list({p['agent_id'] for p in permissions if memory['privacy'] == 'shareable' and ((p['target_type'] == 'memory' and p['target'] == memory['id']) or (p['target_type'] == 'category' and p['target'] == memory['category'])) and any(a['id'] == p['agent_id'] and a['status'] == 'connected' for a in agents)})
    return {'user': user, 'memories': memories, 'agents': agents, 'permissions': permissions, 'activity': activity}

@router.post('/memories', response_model=MemoryResponse, status_code=201)
async def create_memory(data: MemoryInput, user=Depends(owner)):
    if not user.get('vault'): raise HTTPException(409, 'Set up your encrypted vault first')
    memory = {**data.model_dump(), 'id': uid('mem'), 'user_id': user['id'], 'created_at': now(), 'updated_at': now(), 'last_accessed': None}
    await db.memories.insert_one(memory.copy())
    await log(user['id'], 'memory_created', data.title, memory_id=memory['id'])
    return memory

@router.get('/memories/{memory_id}', response_model=MemoryResponse)
async def get_memory(memory_id: str, user=Depends(owner)):
    memory = await owned('memories', memory_id, user)
    await db.memories.update_one({'id': memory_id, 'user_id': user['id']}, {'$set': {'last_accessed': now()}})
    await log(user['id'], 'memory_accessed', memory['title'], memory_id=memory_id)
    return memory

@router.patch('/memories/{memory_id}', response_model=MemoryResponse)
async def update_memory(memory_id: str, data: MemoryInput, user=Depends(owner)):
    old = await owned('memories', memory_id, user)
    changes = {**data.model_dump(), 'updated_at': now()}
    await db.memories.update_one({'id': memory_id, 'user_id': user['id']}, {'$set': changes})
    if data.privacy == 'private':
        perms = await db.permissions.find({'user_id': user['id'], 'target_type': 'memory', 'target': memory_id, 'revoked_at': None}, {'_id': 0}).to_list(200)
        for p in perms:
            await db.permissions.update_one({'id': p['id']}, {'$set': {'revoked_at': now()}})
            await log(user['id'], 'permission_revoked', data.title, p['agent_id'], memory_id)
    await log(user['id'], 'memory_updated', data.title, memory_id=memory_id)
    return {**old, **changes}

@router.delete('/memories/{memory_id}')
async def delete_memory(memory_id: str, user=Depends(owner)):
    memory = await owned('memories', memory_id, user)
    await db.memories.delete_one({'id': memory_id, 'user_id': user['id']})
    await db.permissions.update_many({'user_id': user['id'], 'target_type': 'memory', 'target': memory_id, 'revoked_at': None}, {'$set': {'revoked_at': now()}})
    await log(user['id'], 'memory_deleted', memory['title'], memory_id=memory_id)
    return {'ok': True}

@router.get('/vault/export')
async def export(user=Depends(owner)):
    memories = await db.memories.find({'user_id': user['id']}, {'_id': 0, 'user_id': 0}).to_list(10000)
    await log(user['id'], 'memory_exported', f'Encrypted vault · {len(memories)} memories')
    return {'format': 'cookie-vault', 'version': 1, 'exported_at': now(), 'vault': user['vault'], 'memories': memories}

@router.post('/vault/import', status_code=201)
async def import_vault(data: ImportInput, user=Depends(owner)):
    if not user.get('vault'): raise HTTPException(409, 'Initialize vault first')
    docs = [{**m.model_dump(), 'id': uid('mem'), 'user_id': user['id'], 'created_at': now(), 'updated_at': now(), 'last_accessed': None} for m in data.memories]
    await db.memories.insert_many(docs)
    await log(user['id'], 'memory_imported', f'{len(docs)} encrypted memories imported')
    return {'imported': len(docs)}

@router.delete('/vault/memories')
async def clear_memories(user=Depends(owner)):
    await db.memories.delete_many({'user_id': user['id']})
    await db.permissions.update_many({'user_id': user['id'], 'revoked_at': None}, {'$set': {'revoked_at': now()}})
    await log(user['id'], 'memory_deleted', 'All memories deleted; all permissions revoked')
    return {'ok': True}

@router.get('/agents/catalog')
async def catalog(user=Depends(owner)): return AGENTS

@router.post('/agents', status_code=201)
async def connect_agent(data: AgentInput, user=Depends(owner)):
    agent = {**data.model_dump(), 'id': uid('agent'), 'api_identifier': uid('ck_agent'), 'user_id': user['id'], 'status': 'connected', 'created_at': now(), 'last_activity': None, 'type': 'demo' if data.kind != 'custom' else 'custom'}
    await db.agents.insert_one(agent.copy())
    await log(user['id'], 'agent_connected', data.name, agent['id'])
    return agent

@router.patch('/agents/{agent_id}')
async def agent_status(agent_id: str, data: AgentUpdate, user=Depends(owner)):
    agent = await owned('agents', agent_id, user)
    await db.agents.update_one({'id': agent_id, 'user_id': user['id']}, {'$set': {'status': data.status}})
    if data.status == 'disconnected':
        perms = await db.permissions.find({'user_id': user['id'], 'agent_id': agent_id, 'revoked_at': None}, {'_id': 0}).to_list(5000)
        await db.permissions.update_many({'user_id': user['id'], 'agent_id': agent_id, 'revoked_at': None}, {'$set': {'revoked_at': now()}})
        for p in perms: await log(user['id'], 'permission_revoked', p['target'], agent_id)
    await log(user['id'], 'agent_' + data.status, agent['name'], agent_id)
    return {**agent, 'status': data.status}

@router.post('/permissions', status_code=201)
async def grant(data: PermissionInput, user=Depends(owner)):
    agent = await owned('agents', data.agent_id, user)
    if agent['status'] != 'connected': raise HTTPException(409, 'Connect this agent first')
    title = data.target
    if data.target_type == 'memory':
        memory = await owned('memories', data.target, user)
        if memory['privacy'] != 'shareable': raise HTTPException(403, 'Private memories cannot be shared. Change privacy to Shareable first.')
        title = memory['title']
    elif data.target not in CATEGORIES: raise HTTPException(422, 'Unknown category')
    existing = await db.permissions.find_one({**data.model_dump(), 'user_id': user['id'], 'revoked_at': None}, {'_id': 0})
    if existing: return existing
    permission = {**data.model_dump(), 'id': uid('perm'), 'user_id': user['id'], 'scope': 'read', 'created_at': now(), 'revoked_at': None}
    await db.permissions.insert_one(permission.copy())
    await log(user['id'], 'permission_granted', f'{agent["name"]} → {title}', agent['id'], data.target if data.target_type == 'memory' else None)
    return permission

@router.delete('/permissions/{permission_id}')
async def revoke(permission_id: str, user=Depends(owner)):
    p = await owned('permissions', permission_id, user)
    await db.permissions.update_one({'id': permission_id, 'user_id': user['id']}, {'$set': {'revoked_at': now()}})
    await log(user['id'], 'permission_revoked', p['target'], p['agent_id'])
    return {'ok': True}
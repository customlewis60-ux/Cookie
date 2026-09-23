import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Header
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
def now(): return datetime.now(timezone.utc).isoformat()
def uid(prefix): return prefix + '_' + secrets.token_hex(8)
def digest(value): return hashlib.sha256(value.encode()).hexdigest()

async def owner(authorization: str = Header(default='')):
    token = authorization.removeprefix('Bearer ')
    session = await db.sessions.find_one({'token_hash': digest(token), 'expires_at': {'$gt': now()}}, {'_id': 0})
    if not authorization.startswith('Bearer ') or not session:
        raise HTTPException(401, 'Your session has expired. Connect your demo wallet again.')
    user = await db.users.find_one({'id': session['user_id']}, {'_id': 0, 'credential_hash': 0})
    if not user: raise HTTPException(401, 'Identity not found')
    return user

async def owned(collection, item_id, user):
    item = await db[collection].find_one({'id': item_id, 'user_id': user['id']}, {'_id': 0})
    if not item: raise HTTPException(404, 'Item not found')
    return item

async def log(user_id, action, title, agent_id=None, memory_id=None):
    await db.activity.insert_one({'id': uid('evt'), 'user_id': user_id, 'action': action, 'title': title, 'agent_id': agent_id, 'memory_id': memory_id, 'timestamp': now()})

async def permitted(user_id, agent_id, memory):
    if memory['privacy'] != 'shareable': return False
    return bool(await db.permissions.find_one({'user_id': user_id, 'agent_id': agent_id, 'revoked_at': None, '$or': [{'target_type': 'memory', 'target': memory['id']}, {'target_type': 'category', 'target': memory['category']}]}))

async def new_session(user_id):
    token = secrets.token_urlsafe(48)
    await db.sessions.insert_one({'user_id': user_id, 'token_hash': digest(token), 'expires_at': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()})
    return token

CATEGORIES = ['Personal', 'Preferences', 'Work', 'Trading', 'Projects', 'Knowledge', 'AI Context', 'Custom']
AGENTS = [
    {'name': 'Personal AI', 'developer': 'COOKIE Labs', 'kind': 'personal', 'description': 'A little context. A more personal assistant.'},
    {'name': 'Trading Agent', 'developer': 'COOKIE Labs', 'kind': 'trading', 'description': 'Your strategy, preferences, and risk boundaries.'},
    {'name': 'Coding Agent', 'developer': 'COOKIE Labs', 'kind': 'coding', 'description': 'An agent that knows how you like to build.'},
    {'name': 'Research Agent', 'developer': 'COOKIE Labs', 'kind': 'research', 'description': 'Connect your knowledge to your next discovery.'},
]
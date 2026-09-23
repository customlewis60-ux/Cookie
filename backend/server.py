import os
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).parent / '.env')
from core import db, client
from routes import router
from developer import router as developer_router

@asynccontextmanager
async def lifespan(app):
    await db.users.create_index('credential_hash', unique=True)
    await db.sessions.create_index('token_hash', unique=True)
    await db.api_keys.create_index('key_hash', unique=True)
    await db.memories.create_index([('user_id', 1), ('created_at', -1)])
    await db.permissions.create_index([('user_id', 1), ('agent_id', 1)])
    yield
    client.close()

app = FastAPI(title='COOKIE Memory API', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.environ['CORS_ORIGINS'].split(','), allow_credentials=False, allow_methods=['GET', 'POST', 'PATCH', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])
app.include_router(router, prefix='/api')
app.include_router(developer_router, prefix='/api')

@app.get('/api/health')
async def health():
    await db.command('ping')
    return {'status': 'ok', 'product': 'COOKIE', 'version': '0.1.0'}
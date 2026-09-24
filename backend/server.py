import os
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).parent / '.env')
from core import db, client
from routes import router
from developer import router as developer_router
from studio import router as studio_router

@asynccontextmanager
async def lifespan(app):
    await db.users.create_index('credential_hash', unique=True)
    await db.sessions.create_index('token_hash', unique=True)
    await db.api_keys.create_index('key_hash', unique=True)
    await db.memories.create_index([('user_id', 1), ('created_at', -1)])
    await db.permissions.create_index([('user_id', 1), ('agent_id', 1)])
    await db.studio_preparations.create_index('token_hash', unique=True)
    await db.studio_preparations.create_index('expires_at', expireAfterSeconds=0)
    await db.studio_slots.create_index('user_id', unique=True)
    await db.studio_slots.create_index('expires_at', expireAfterSeconds=0)
    await db.studio_budgets.create_index('id', unique=True)
    await db.studio_budgets.create_index('expires_at', expireAfterSeconds=0)
    await db.studio_runs.create_index([('user_id', 1), ('created_at', -1)])
    yield
    client.close()

app = FastAPI(title='COOKIE Memory API', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.environ['CORS_ORIGINS'].split(','), allow_credentials=False, allow_methods=['GET', 'POST', 'PATCH', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])
app.include_router(router, prefix='/api')
app.include_router(developer_router, prefix='/api')
app.include_router(studio_router, prefix='/api')

@app.exception_handler(RequestValidationError)
async def safe_validation(request, exc):
    if request.url.path.startswith('/api/studio/'):
        # FastAPI's default validation details can echo rejected plaintext inputs.
        return JSONResponse(status_code=422, content={'detail': 'Invalid task request. Check consent, task length and selected memory limits; no input content was recorded.'}, headers={'Cache-Control': 'no-store'})
    return await request_validation_exception_handler(request, exc)

@app.get('/api/health')
async def health():
    await db.command('ping')
    return {'status': 'ok', 'product': 'COOKIE', 'version': '0.1.0'}
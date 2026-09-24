import os
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pymongo import ReturnDocument
from core import db, now, uid, digest, owner, log
from studio_models import PrepareInput, ExecuteInput, PreparedResponse, RunReceipt, StudioConfig
from studio_guard import utcnow, payload_version, authorize, record_denial, acquire_slot, release_slot, check_budget
from studio_stream import run_stream

router = APIRouter(prefix='/studio')


def config():
    return {'configured': bool(os.environ.get('EMERGENT_LLM_KEY')), 'provider': 'OpenAI via Emergent',
            'model': os.environ['COOKIE_AI_MODEL'], 'model_label': 'GPT-5.4 Mini',
            'timeout_seconds': int(os.environ['COOKIE_AI_TIMEOUT_SECONDS']),
            'hourly_limit': int(os.environ['COOKIE_AI_USER_HOURLY_LIMIT'])}


@router.get('/config', response_model=StudioConfig)
async def studio_config(user=Depends(owner)):
    return config()


@router.post('/prepare', response_model=PreparedResponse)
async def prepare(data: PrepareInput, user=Depends(owner)):
    if not user.get('vault'):
        raise HTTPException(409, 'Initialize and unlock your vault before running an agent task.')
    try:
        _, memories = await authorize(user, data.agent_id, data.memory_ids)
    except HTTPException:
        await record_denial(user, data.agent_id)
        raise
    token = secrets.token_urlsafe(40)
    expires = utcnow() + timedelta(minutes=5)
    record = {'token_hash': digest(token), 'user_id': user['id'], 'agent_id': data.agent_id,
              'task_digest': data.task_digest, 'expires_at': expires, 'used_at': None,
              'snapshots': {m['id']: {'updated_at': m['updated_at'], 'version': payload_version(m)} for m in memories}}
    await db.studio_preparations.insert_one(record)
    await log(user['id'], 'context_review_requested', f'Agent Studio · {len(memories)} encrypted memories · not yet sent to AI', data.agent_id)
    return {'consent_token': token, 'expires_at': expires.isoformat(), 'provider': config()['provider'], 'model': config()['model'], 'memories': memories}


@router.post('/execute')
async def execute(data: ExecuteInput, request: Request, user=Depends(owner), authorization: str = Header()):
    settings = config()
    if not settings['configured']:
        raise HTTPException(503, 'The AI provider is not configured. Your context has not been sent.')
    query = {'token_hash': digest(data.consent_token), 'user_id': user['id'], 'used_at': None, 'expires_at': {'$gt': utcnow()}}
    preparation = await db.studio_preparations.find_one(query, {'_id': 0})
    if not preparation:
        raise HTTPException(409, 'This review expired or was already used. Review and approve a new task.')
    if digest(data.task) != preparation['task_digest'] or set(c.memory_id for c in data.contexts) != set(preparation['snapshots']):
        raise HTTPException(409, 'The task or selected memories changed after review. Review and approve again.')
    try:
        agent, _ = await authorize(user, preparation['agent_id'], list(preparation['snapshots']), preparation['snapshots'])
    except HTTPException:
        await record_denial(user, preparation['agent_id'])
        raise
    run_id = uid('run')
    await acquire_slot(user['id'], run_id, settings['timeout_seconds'])
    try:
        # Single-use consumption is atomic even if two browser requests race.
        used = await db.studio_preparations.find_one_and_update(query, {'$set': {'used_at': now()}}, projection={'_id': 0}, return_document=ReturnDocument.AFTER)
        if not used:
            raise HTTPException(409, 'This review was already used. Review and approve a new task.')
        await check_budget(user['id'], settings['hourly_limit'], int(os.environ['COOKIE_AI_DAILY_LIMIT']))
        receipt = {'id': run_id, 'user_id': user['id'], 'agent_id': agent['id'], 'agent_name': agent['name'],
                   'provider': settings['provider'], 'model': settings['model'], 'memory_ids': list(preparation['snapshots']),
                   'memory_count': len(preparation['snapshots']), 'status': 'running', 'created_at': now(), 'cancel_requested': False}
        await db.studio_runs.insert_one(receipt.copy())
    except Exception:
        await release_slot(user['id'], run_id)
        raise
    # The approved plaintext passes transiently through this authenticated runtime
    # and the model gateway. Only the explicit metadata receipt is persisted.
    return StreamingResponse(run_stream(request, user, agent, preparation, data, receipt, authorization, settings['timeout_seconds']),
                             media_type='text/event-stream', headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


@router.get('/runs', response_model=list[RunReceipt])
async def runs(user=Depends(owner)):
    # Recover metadata for a request interrupted by a process restart.
    stale_before = (utcnow() - timedelta(seconds=config()['timeout_seconds'] + 30)).isoformat()
    await db.studio_runs.update_many({'user_id': user['id'], 'status': 'running', 'created_at': {'$lt': stale_before}}, {'$set': {'status': 'failed', 'error_code': 'interrupted', 'finished_at': now()}})
    return await db.studio_runs.find({'user_id': user['id']}, {'_id': 0, 'user_id': 0, 'cancel_requested': 0}).sort('created_at', -1).to_list(30)


@router.post('/runs/{run_id}/cancel')
async def cancel(run_id: str, user=Depends(owner)):
    result = await db.studio_runs.update_one({'id': run_id, 'user_id': user['id'], 'status': 'running'}, {'$set': {'cancel_requested': True}})
    if not result.matched_count:
        raise HTTPException(404, 'This task is no longer running or does not belong to you.')
    return {'ok': True}
from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.adapters import gmail
from app.adapters.errors import AdapterError
from app.adapters.mappers import map_message
from app.agents.triage import get_triage_verdict

router = APIRouter()


@router.get("/api/triage/{message_id}")
async def get_triage(message_id: str):
    try:
        raw = await run_in_threadpool(gmail.get_message, message_id)
    except AdapterError as e:
        raise HTTPException(status_code=502, detail=str(e))

    message = map_message(raw)
    return await get_triage_verdict(message)

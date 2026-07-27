import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.governance.traces import new_trace_id
from app.ledger.service import execute_action
from app.schemas import ActionDescriptor, Authorization

router = APIRouter()


class ExecuteRequest(BaseModel):
    descriptor: ActionDescriptor
    authorization: Authorization
    idempotency_key: uuid.UUID


@router.post("/api/actions/execute")
async def post_execute(body: ExecuteRequest, db: Session = Depends(get_db)):
    return await execute_action(db, body.descriptor, body.authorization, body.idempotency_key, new_trace_id())

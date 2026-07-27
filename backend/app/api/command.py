from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents import manager, policy_gate
from app.db import get_db
from app.governance.traces import new_trace_id
from app.ledger.models import Clarification

router = APIRouter()


class CommandRequest(BaseModel):
    text: str
    context: dict | None = None


class ClarifyRequest(BaseModel):
    clarification_id: str
    answer: str
    save_as_policy: bool = True


@router.post("/api/command")
async def post_command(body: CommandRequest, db: Session = Depends(get_db)):
    trace_id = new_trace_id()
    return await manager.handle_command(db, body.text, body.context, trace_id)


@router.post("/api/clarify")
async def post_clarify(body: ClarifyRequest, db: Session = Depends(get_db)):
    clarification = db.get(Clarification, body.clarification_id)
    if clarification is None:
        raise HTTPException(status_code=404, detail="clarification not found")

    trace_id = new_trace_id()
    saved_policy_id = await policy_gate.learn(db, clarification, body.answer, body.save_as_policy, trace_id)

    result = await manager.handle_command(db, clarification.instruction_text, None, trace_id)
    if saved_policy_id:
        result["saved_policy_id"] = saved_policy_id
    return result

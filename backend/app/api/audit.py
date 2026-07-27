from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.ledger.models import Action
from app.ledger.undo import IrreversibleActionError, UndoNotAvailableError, undo_action

router = APIRouter()


def _serialize(a: Action) -> dict:
    return {
        "id": str(a.id),
        "created_at": a.created_at,
        "actor": a.actor,
        "agent_name": a.agent_name,
        "tool": a.tool,
        "operation": a.operation,
        "params_json": a.params_json,
        "authorization_type": a.authorization_type,
        "authorization_ref": a.authorization_ref,
        "lyzr_trace_id": a.lyzr_trace_id,
        "idempotency_key": str(a.idempotency_key),
        "status": a.status,
        "result_json": a.result_json,
        "inverse_operation": a.inverse_operation,
        "inverse_params_json": a.inverse_params_json,
        "irreversible": a.irreversible,
        "undone_at": a.undone_at,
        "undone_by": a.undone_by,
    }


@router.get("/api/audit")
async def list_audit(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.execute(select(Action).order_by(Action.created_at.desc()).limit(limit)).scalars().all()
    return [_serialize(a) for a in rows]


@router.post("/api/audit/{action_id}/undo")
async def post_undo(action_id: str, db: Session = Depends(get_db)):
    action = db.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="action not found")

    try:
        result = await undo_action(db, action)
    except IrreversibleActionError:
        raise HTTPException(status_code=409, detail={"error": "irreversible", "hint": "draft a correction instead"})
    except UndoNotAvailableError:
        raise HTTPException(status_code=409, detail={"error": "not_undoable", "hint": "action is not in an executed state"})

    return {"status": "undone", "undo_action_id": result.get("action_id")}

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ledger.models import Action
from app.ledger.service import execute_action
from app.schemas import ActionDescriptor, Authorization


class IrreversibleActionError(Exception):
    pass


class UndoNotAvailableError(Exception):
    pass


async def undo_action(db: Session, action: Action) -> dict:
    if action.irreversible:
        raise IrreversibleActionError()
    if action.status != "executed":
        raise UndoNotAvailableError()

    descriptor = ActionDescriptor(
        tool=action.tool,
        operation=action.inverse_operation,
        params=action.inverse_params_json or {},
        agent_name=None,
    )
    authorization = Authorization(type="instruction", ref=f"undo:{action.id}")

    result = await execute_action(
        db,
        descriptor,
        authorization,
        idempotency_key=uuid.uuid4(),
        trace_id=action.lyzr_trace_id,
        skip_gate=True,
    )

    action.status = "undone"
    action.undone_at = datetime.now(timezone.utc)
    action.undone_by = "user"
    db.add(action)
    db.commit()

    return result

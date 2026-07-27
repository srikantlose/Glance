import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.adapters import gcal, gmail, gtasks
from app.adapters.errors import AdapterError
from app.governance import hitl_gate, pii_guard
from app.ledger.inverse_ops import CREATE_OPS_NEEDING_ID_PATCH, compute_inverse
from app.ledger.models import Action, Outbox
from app.schemas import ActionDescriptor, Authorization


def _delete_event(params: dict) -> dict:
    gcal.delete_event(params["event_id"])
    return {"event_id": params["event_id"]}


def _delete_task(params: dict) -> dict:
    gtasks.delete_task(params["task_id"])
    return {"task_id": params["task_id"]}


DISPATCH = {
    ("gmail", "archive"): lambda p: gmail.archive(p["message_id"]),
    ("gmail", "unarchive"): lambda p: gmail.unarchive(p["message_id"]),
    ("gmail", "label.add"): lambda p: gmail.label_add(p["message_id"], p["label_id"]),
    ("gmail", "label.remove"): lambda p: gmail.label_remove(p["message_id"], p["label_id"]),
    ("gmail", "send"): lambda p: gmail.send(p["to"], p["subject"], p["body"], p.get("thread_id")),
    ("calendar", "event.create"): lambda p: gcal.create_event(p["body"]),
    ("calendar", "event.move"): lambda p: gcal.move_event(p["event_id"], p["new_start"], p["new_end"]),
    ("calendar", "event.delete"): _delete_event,
    ("tasks", "task.create"): lambda p: gtasks.create_task(p["title"], p.get("notes"), p.get("due")),
    ("tasks", "task.complete"): lambda p: gtasks.complete_task(p["task_id"]),
    ("tasks", "task.uncomplete"): lambda p: gtasks.uncomplete_task(p["task_id"]),
    ("tasks", "task.delete"): _delete_task,
}


def _outbound_text(descriptor: ActionDescriptor) -> str | None:
    if descriptor.tool == "gmail" and descriptor.operation == "send":
        return descriptor.params.get("body", "")
    return None


def _render_preview(descriptor: ActionDescriptor) -> str:
    p = descriptor.params
    if descriptor.tool == "gmail" and descriptor.operation == "send":
        return f"To: {p.get('to')}\nSubject: {p.get('subject')}\n\n{p.get('body')}"
    if descriptor.tool == "calendar" and descriptor.operation == "event.delete":
        return f"Delete calendar event {p.get('event_id')}"
    if descriptor.tool == "calendar" and descriptor.operation == "event.move":
        return f"Move event {p.get('event_id')} to {p.get('new_start')}"
    return f"{descriptor.tool}.{descriptor.operation}({p})"


def _fetch_original(descriptor: ActionDescriptor) -> dict | None:
    if descriptor.tool == "calendar" and descriptor.operation in ("event.move", "event.delete"):
        return gcal.get_event(descriptor.params["event_id"])
    return None


async def execute_action(
    db: Session,
    descriptor: ActionDescriptor,
    authorization: Authorization,
    idempotency_key: uuid.UUID,
    trace_id: str | None = None,
    skip_gate: bool = False,
) -> dict:
    """skip_gate is for undo only -- clicking Undo is itself the user's authorization,
    so the inverse shouldn't have to go stand in the approval queue again (e.g. undoing
    an event.create means running event.delete, which is normally always gated)."""
    existing = db.execute(
        select(Action).where(Action.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing is not None and existing.status == "executed":
        return {"status": "executed", "action_id": str(existing.id), "result": existing.result_json}

    if not skip_gate and hitl_gate.requires_approval(descriptor) and authorization.type != "approval":
        text = _outbound_text(descriptor)
        findings = await pii_guard.full_scan(text) if text else []
        approval = hitl_gate.create_approval(db, [descriptor], _render_preview(descriptor), findings)
        return {"status": "needs_approval", "approval_id": str(approval.id)}

    original = await run_in_threadpool(_fetch_original, descriptor)
    inverse_operation, inverse_params, irreversible = compute_inverse(
        descriptor.tool, descriptor.operation, descriptor.params, original
    )

    if existing is None:
        action = Action(
            actor="user" if authorization.type == "approval" else "agent",
            agent_name=descriptor.agent_name,
            tool=descriptor.tool,
            operation=descriptor.operation,
            params_json=descriptor.params,
            authorization_type=authorization.type,
            authorization_ref=authorization.ref,
            lyzr_trace_id=trace_id,
            idempotency_key=idempotency_key,
            status="pending",
            inverse_operation=inverse_operation,
            inverse_params_json=inverse_params,
            irreversible=irreversible,
        )
        db.add(action)
        db.commit()
        db.refresh(action)
    else:
        action = existing

    handler = DISPATCH.get((descriptor.tool, descriptor.operation))
    if handler is None:
        raise ValueError(f"no adapter mapped for {descriptor.tool}.{descriptor.operation}")

    try:
        result = await run_in_threadpool(handler, descriptor.params)
    except AdapterError:
        action.status = "queued"
        db.add(action)
        db.add(Outbox(action_id=action.id, next_attempt_at=datetime.now(timezone.utc)))
        db.commit()
        return {"status": "queued", "action_id": str(action.id)}

    action.status = "executed"
    action.result_json = result

    patch_key = CREATE_OPS_NEEDING_ID_PATCH.get((descriptor.tool, descriptor.operation))
    if patch_key and action.inverse_params_json is not None:
        param_name, result_field = patch_key
        action.inverse_params_json = {**action.inverse_params_json, param_name: result.get(result_field)}

    db.add(action)
    db.commit()
    db.refresh(action)
    return {"status": "executed", "action_id": str(action.id), "result": result}

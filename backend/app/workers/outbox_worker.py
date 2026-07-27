from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.adapters.errors import AdapterError
from app.config import OUTBOX_DEAD_AFTER_ATTEMPTS
from app.db import SessionLocal
from app.ledger.models import Action, Outbox
from app.ledger.service import DISPATCH


async def run_outbox_pass() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        rows = db.execute(
            select(Outbox).where(Outbox.status == "waiting", Outbox.next_attempt_at <= now)
        ).scalars().all()

        for row in rows:
            action = db.get(Action, row.action_id)
            if action is None:
                row.status = "dead"
                row.last_error = "orphaned outbox row: action missing"
                db.add(row)
                continue

            handler = DISPATCH.get((action.tool, action.operation))
            if handler is None:
                row.status = "dead"
                row.last_error = f"no adapter for {action.tool}.{action.operation}"
                db.add(row)
                continue

            try:
                result = await run_in_threadpool(handler, action.params_json)
            except AdapterError as e:
                row.attempts += 1
                row.last_error = str(e)
                if row.attempts >= OUTBOX_DEAD_AFTER_ATTEMPTS:
                    row.status = "dead"
                else:
                    row.next_attempt_at = now + timedelta(seconds=30 * (2 ** row.attempts))
                db.add(row)
                continue

            action.status = "executed"
            action.result_json = result
            row.status = "succeeded"
            db.add(action)
            db.add(row)

        db.commit()
    finally:
        db.close()

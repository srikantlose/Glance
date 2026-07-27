import sys
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app import state
from app.config import settings
from app.db import get_db
from app.ledger.models import Action, Approval, Clarification, Outbox

router = APIRouter()

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _check_token(x_demo_token: str | None) -> None:
    if not settings.DEMO_TOKEN or x_demo_token != settings.DEMO_TOKEN:
        raise HTTPException(status_code=401, detail="missing or bad X-Demo-Token")


class FailureModeRequest(BaseModel):
    mode: str  # "off" | "gmail_401"


@router.post("/api/demo/failure-mode")
async def set_failure_mode(body: FailureModeRequest, x_demo_token: str | None = Header(default=None)):
    _check_token(x_demo_token)
    if body.mode not in ("off", "gmail_401"):
        raise HTTPException(status_code=400, detail="mode must be 'off' or 'gmail_401'")
    state.runtime_flags["failure_mode"] = body.mode
    return {"failure_mode": state.runtime_flags["failure_mode"]}


@router.post("/api/demo/reseed")
async def reseed(x_demo_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    _check_token(x_demo_token)

    import seed
    import seed_memory

    # outbox references actions, so it has to go first
    db.execute(delete(Outbox))
    db.execute(delete(Action))
    db.execute(delete(Approval))
    db.execute(delete(Clarification))
    db.commit()

    google_summary = seed.run_seed()
    memory_summary = await seed_memory.run_seed_memory()
    state.clear_caches()

    return {"google": google_summary, "memory": memory_summary}

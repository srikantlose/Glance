import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.governance.traces import new_trace_id
from app.ledger.models import Approval
from app.ledger.service import execute_action
from app.schemas import ActionDescriptor, Authorization

router = APIRouter()


@router.get("/api/approvals")
async def list_approvals(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Approval).where(Approval.status == "pending").order_by(Approval.created_at.desc())
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "created_at": r.created_at,
            "preview": r.action_preview_json,
            "pii_findings": r.pii_findings_json,
            "status": r.status,
        }
        for r in rows
    ]


@router.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: str, db: Session = Depends(get_db)):
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail=f"approval already {approval.status}")

    trace_id = new_trace_id()
    authorization = Authorization(type="approval", ref=str(approval.id))

    results = []
    for action_data in approval.action_preview_json.get("actions", []):
        descriptor = ActionDescriptor(**action_data)
        result = await execute_action(db, descriptor, authorization, idempotency_key=uuid.uuid4(), trace_id=trace_id)
        results.append(result)

    approval.status = "approved"
    approval.decided_at = datetime.now(timezone.utc)
    db.add(approval)
    db.commit()

    return {"status": "approved", "results": results}


@router.post("/api/approvals/{approval_id}/reject")
async def reject(approval_id: str, db: Session = Depends(get_db)):
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail=f"approval already {approval.status}")

    approval.status = "rejected"
    approval.decided_at = datetime.now(timezone.utc)
    db.add(approval)
    db.commit()

    return {"status": "rejected"}

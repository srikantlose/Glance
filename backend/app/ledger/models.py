import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.ledger.types import GUID


class Base(DeclarativeBase):
    pass


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor: Mapped[str] = mapped_column(String, nullable=False)  # 'agent' | 'user'
    agent_name: Mapped[str | None] = mapped_column(String, nullable=True)
    tool: Mapped[str] = mapped_column(String, nullable=False)  # 'gmail' | 'calendar' | 'tasks'
    operation: Mapped[str] = mapped_column(String, nullable=False)
    params_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    authorization_type: Mapped[str] = mapped_column(String, nullable=False)  # 'policy'|'instruction'|'approval'
    authorization_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    lyzr_trace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(GUID(), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    inverse_operation: Mapped[str | None] = mapped_column(String, nullable=True)
    inverse_params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    irreversible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    undone_by: Mapped[str | None] = mapped_column(String, nullable=True)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    action_preview_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    pii_findings_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending|approved|rejected
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Outbox(Base):
    __tablename__ = "outbox"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    action_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("actions.id"), nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="waiting")  # waiting|succeeded|dead


class Clarification(Base):
    __tablename__ = "clarifications"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    instruction_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resulting_policy_id: Mapped[str | None] = mapped_column(String, nullable=True)

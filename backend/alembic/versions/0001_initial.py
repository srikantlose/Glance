"""initial tables: actions, approvals, outbox, clarifications

Revision ID: 0001
Revises:
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("actor", sa.String, nullable=False),
        sa.Column("agent_name", sa.String, nullable=True),
        sa.Column("tool", sa.String, nullable=False),
        sa.Column("operation", sa.String, nullable=False),
        sa.Column("params_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("authorization_type", sa.String, nullable=False),
        sa.Column("authorization_ref", sa.Text, nullable=True),
        sa.Column("lyzr_trace_id", sa.String, nullable=True),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("result_json", postgresql.JSONB, nullable=True),
        sa.Column("inverse_operation", sa.String, nullable=True),
        sa.Column("inverse_params_json", postgresql.JSONB, nullable=True),
        sa.Column("irreversible", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("undone_by", sa.String, nullable=True),
    )
    op.create_unique_constraint("uq_actions_idempotency_key", "actions", ["idempotency_key"])
    op.create_index("ix_actions_idempotency_key", "actions", ["idempotency_key"])
    op.create_index("ix_actions_created_at", "actions", ["created_at"])

    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("action_preview_json", postgresql.JSONB, nullable=False),
        sa.Column("pii_findings_json", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("actions.id"), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="waiting"),
    )
    op.create_index("ix_outbox_next_attempt_at", "outbox", ["next_attempt_at"])

    op.create_table(
        "clarifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("instruction_text", sa.Text, nullable=False),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("answer_text", sa.Text, nullable=True),
        sa.Column("resulting_policy_id", sa.String, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("clarifications")
    op.drop_index("ix_outbox_next_attempt_at", table_name="outbox")
    op.drop_table("outbox")
    op.drop_table("approvals")
    op.drop_index("ix_actions_created_at", table_name="actions")
    op.drop_index("ix_actions_idempotency_key", table_name="actions")
    op.drop_constraint("uq_actions_idempotency_key", "actions", type_="unique")
    op.drop_table("actions")

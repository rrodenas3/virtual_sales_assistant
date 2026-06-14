"""initial portable schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(), primary_key=True),
        sa.Column("rep_id", sa.String(), nullable=False),
        sa.Column("territory_code", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sessions_rep_id", "sessions", ["rep_id"])
    op.create_index("ix_sessions_territory_code", "sessions", ["territory_code"])

    op.create_table(
        "alert_feedback",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("alert_id", sa.String(), nullable=False),
        sa.Column("store_id", sa.String(), nullable=False),
        sa.Column("sku_id", sa.String(), nullable=False),
        sa.Column("rep_id", sa.String(), nullable=False),
        sa.Column("feedback", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_feedback_alert_id", "alert_feedback", ["alert_id"])
    op.create_index("ix_alert_feedback_store_id", "alert_feedback", ["store_id"])
    op.create_index("ix_alert_feedback_rep_id", "alert_feedback", ["rep_id"])
    op.create_index("ix_alert_feedback_session_id", "alert_feedback", ["session_id"])

    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("rep_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("data_freshness_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_session_id", "audit_events", ["session_id"])
    op.create_index("ix_audit_events_rep_id", "audit_events", ["rep_id"])

    op.create_table(
        "visit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("store_id", sa.String(), nullable=False),
        sa.Column("rep_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "order_drafts",
        sa.Column("draft_id", sa.String(), primary_key=True),
        sa.Column("store_id", sa.String(), nullable=False),
        sa.Column("rep_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "approval_records",
        sa.Column("approval_id", sa.String(), primary_key=True),
        sa.Column("draft_id", sa.String(), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("approved_by", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("draft_payload_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "idempotency_records",
        sa.Column("idempotency_key", sa.String(), primary_key=True),
        sa.Column("rep_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_idempotency_records_rep_id", "idempotency_records", ["rep_id"])


def downgrade() -> None:
    for table in [
        "idempotency_records",
        "approval_records",
        "order_drafts",
        "visit_logs",
        "audit_events",
        "alert_feedback",
        "sessions",
    ]:
        op.drop_table(table)

"""add manager tasks

Revision ID: 0002_manager_tasks
Revises: 0001_initial
Create Date: 2026-06-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_manager_tasks"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manager_tasks",
        sa.Column("task_id", sa.String(), primary_key=True),
        sa.Column("territory_code", sa.String(), nullable=False),
        sa.Column("store_id", sa.String(), nullable=False),
        sa.Column("assigned_rep_id", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("due_date", sa.String(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_manager_tasks_territory_code", "manager_tasks", ["territory_code"])
    op.create_index("ix_manager_tasks_store_id", "manager_tasks", ["store_id"])
    op.create_index("ix_manager_tasks_assigned_rep_id", "manager_tasks", ["assigned_rep_id"])
    op.create_index("ix_manager_tasks_session_id", "manager_tasks", ["session_id"])


def downgrade() -> None:
    op.drop_table("manager_tasks")

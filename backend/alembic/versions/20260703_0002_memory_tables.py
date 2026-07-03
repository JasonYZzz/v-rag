"""memory tables

Revision ID: 20260703_0002
Revises: 20260703_0001
Create Date: 2026-07-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260703_0002"
down_revision: str | None = "20260703_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_event",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("sensitivity", sa.String(), nullable=False),
        sa.Column("source_event_id", sa.String(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column("ttl", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "memory_fact",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("predicate", sa.String(), nullable=False),
        sa.Column("object", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source_event_id", sa.String(), nullable=True),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "memory_procedure",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("skill_name", sa.String(), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("action_spec", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "memory_feedback",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("memory_id", sa.String(), nullable=False),
        sa.Column("memory_type", sa.String(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "memory_consolidation_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("memory_consolidation_log")
    op.drop_table("memory_feedback")
    op.drop_table("memory_procedure")
    op.drop_table("memory_fact")
    op.drop_table("memory_event")

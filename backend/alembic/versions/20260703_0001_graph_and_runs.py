"""Initial schema with graph config and run trace."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260703_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration."""

    op.create_table(
        "document",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("parser", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "agent_graph_config",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("current_published_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "run_trace",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("graph_config_id", sa.String(), nullable=True),
        sa.Column("graph_version", sa.Integer(), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("route_trace", sa.JSON(), nullable=False),
        sa.Column("node_io", sa.JSON(), nullable=False),
        sa.Column("intent", sa.String(), nullable=True),
        sa.Column("budget", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "chunk",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("heading_path", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "agent_graph_publish_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("config_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["config_id"], ["agent_graph_config.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "agent_graph_version",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("config_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("graph", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["config_id"], ["agent_graph_config.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_id", "version", name="uq_graph_config_version"),
    )


def downgrade() -> None:
    """Revert migration."""

    op.drop_table("agent_graph_version")
    op.drop_table("agent_graph_publish_history")
    op.drop_table("chunk")
    op.drop_table("run_trace")
    op.drop_table("agent_graph_config")
    op.drop_table("document")

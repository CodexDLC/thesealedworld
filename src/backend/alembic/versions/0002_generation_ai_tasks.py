"""generation ai task queue

Revision ID: 0002_generation_ai_tasks
Revises: 0001_game_schema_baseline
Create Date: 2026-05-15 12:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_generation_ai_tasks"
down_revision: str | Sequence[str] | None = "0001_game_schema_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_generation_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("identity_key", sa.String(length=128), nullable=False),
        sa.Column("task_type", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=160), nullable=False),
        sa.Column("season_id", sa.String(length=80), nullable=True),
        sa.Column("output_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("asset_hash", sa.String(length=128), nullable=True),
        sa.Column("storage_prefix", sa.String(length=240), nullable=True),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("generated_url", sa.String(length=1000), nullable=True),
        sa.Column("prompt_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_generation_tasks")),
        sa.UniqueConstraint("identity_key", name="uq_ai_generation_task_identity_key"),
        if_not_exists=True,
    )
    for column in (
        "asset_hash",
        "batch_id",
        "entity_id",
        "entity_type",
        "identity_key",
        "model",
        "not_before",
        "output_kind",
        "priority",
        "season_id",
        "status",
        "storage_key",
        "task_type",
    ):
        op.create_index(
            op.f(f"ix_ai_generation_tasks_{column}"),
            "ai_generation_tasks",
            [column],
            unique=False,
            if_not_exists=True,
        )


def downgrade() -> None:
    op.drop_table("ai_generation_tasks")

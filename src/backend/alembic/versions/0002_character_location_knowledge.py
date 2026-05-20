"""add character location knowledge

Revision ID: 0002_location_knowledge
Revises: 0001_game_schema_baseline
Create Date: 2026-05-20 01:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_location_knowledge"
down_revision: str | Sequence[str] | None = "0001_game_schema_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "character_location_knowledge",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("loc_id", sa.String(length=64), nullable=False),
        sa.Column("movement_xp_spent", sa.Float(), nullable=False),
        sa.Column("scouting_xp_spent", sa.Float(), nullable=False),
        sa.Column("hunting_xp_spent", sa.Float(), nullable=False),
        sa.Column("movement_xp_cap", sa.Float(), nullable=False),
        sa.Column("scouting_xp_cap", sa.Float(), nullable=False),
        sa.Column("hunting_xp_cap", sa.Float(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_visited_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.character_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("character_id", "loc_id", name="uq_character_location_knowledge_character_loc"),
    )
    op.create_index(
        "ix_character_location_knowledge_character_id",
        "character_location_knowledge",
        ["character_id"],
        unique=False,
    )
    op.create_index("ix_character_location_knowledge_loc_id", "character_location_knowledge", ["loc_id"], unique=False)
    op.create_index(
        "ix_character_location_knowledge_character_updated",
        "character_location_knowledge",
        ["character_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_character_location_knowledge_character_updated", table_name="character_location_knowledge")
    op.drop_index("ix_character_location_knowledge_loc_id", table_name="character_location_knowledge")
    op.drop_index("ix_character_location_knowledge_character_id", table_name="character_location_knowledge")
    op.drop_table("character_location_knowledge")

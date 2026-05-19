"""add character npc states

Revision ID: 0008_character_npc_states
Revises: 0007_item_generated_templates
Create Date: 2026-05-19 15:20:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0008_character_npc_states"
down_revision: str | None = "0007_item_generated_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

if TYPE_CHECKING:
    from collections.abc import Sequence


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "character_npc_states" not in tables:
        op.create_table(
            "character_npc_states",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("character_id", sa.Integer(), nullable=False),
            sa.Column("npc_key", sa.String(length=96), nullable=False),
            sa.Column("reputation", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("affinity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
            sa.Column(
                "counters",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("last_interaction_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["character_id"], ["characters.character_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("character_id", "npc_key", name="uq_character_npc_states_character_npc"),
        )
    _create_index_once("ix_character_npc_states_character_id", "character_npc_states", ["character_id"])
    _create_index_once("ix_character_npc_states_npc_key", "character_npc_states", ["npc_key"])

    if "character_npc_effect_logs" not in tables:
        op.create_table(
            "character_npc_effect_logs",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("character_id", sa.Integer(), nullable=False),
            sa.Column("npc_key", sa.String(length=96), nullable=False),
            sa.Column("idempotency_key", sa.String(length=200), nullable=False),
            sa.Column("effect_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["character_id"], ["characters.character_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "character_id",
                "npc_key",
                "idempotency_key",
                name="uq_character_npc_effect_logs_character_npc_idempotency",
            ),
        )
    _create_index_once("ix_character_npc_effect_logs_character_id", "character_npc_effect_logs", ["character_id"])
    _create_index_once("ix_character_npc_effect_logs_npc_key", "character_npc_effect_logs", ["npc_key"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "character_npc_effect_logs" in tables:
        for index_name in ("ix_character_npc_effect_logs_npc_key", "ix_character_npc_effect_logs_character_id"):
            if index_name in {index["name"] for index in inspector.get_indexes("character_npc_effect_logs")}:
                op.drop_index(index_name, table_name="character_npc_effect_logs")
        op.drop_table("character_npc_effect_logs")
    if "character_npc_states" in tables:
        for index_name in ("ix_character_npc_states_npc_key", "ix_character_npc_states_character_id"):
            if index_name in {index["name"] for index in inspector.get_indexes("character_npc_states")}:
                op.drop_index(index_name, table_name="character_npc_states")
        op.drop_table("character_npc_states")


def _create_index_once(index_name: str, table_name: str, columns: list[str]) -> None:
    existing = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)

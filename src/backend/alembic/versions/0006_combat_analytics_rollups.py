"""add combat analytics facts and rollups

Revision ID: 0006_combat_analytics_rollups
Revises: 0005_character_name_key
Create Date: 2026-05-17 14:30:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0006_combat_analytics_rollups"
down_revision: str | None = "0005_character_name_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

if TYPE_CHECKING:
    from collections.abc import Sequence


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "combat_exchange_facts" not in tables:
        op.create_table(
            "combat_exchange_facts",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("combat_id", sa.String(length=64), nullable=False),
            sa.Column("turn", sa.Integer(), nullable=False),
            sa.Column("wave", sa.Integer(), nullable=False),
            sa.Column("seq", sa.Integer(), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("battle_type", sa.String(length=40), nullable=True),
            sa.Column("location_id", sa.String(length=120), nullable=True),
            sa.Column("source_actor_id", sa.String(length=64), nullable=True),
            sa.Column("target_actor_id", sa.String(length=64), nullable=True),
            sa.Column("action_id", sa.String(length=120), nullable=True),
            sa.Column("feint_id", sa.String(length=120), nullable=True),
            sa.Column("outcome", sa.String(length=32), nullable=True),
            sa.Column("source_type", sa.String(length=40), nullable=True),
            sa.Column("is_crit", sa.Boolean(), nullable=False),
            sa.Column("is_counter", sa.Boolean(), nullable=False),
            sa.Column("is_extra_strike", sa.Boolean(), nullable=False),
            sa.Column("weapon_base_id", sa.String(length=120), nullable=True),
            sa.Column("weapon_tier", sa.Integer(), nullable=True),
            sa.Column("weapon_power", sa.Float(), nullable=True),
            sa.Column("armor_class", sa.String(length=40), nullable=True),
            sa.Column("armor_tier", sa.Integer(), nullable=True),
            sa.Column("raw_damage", sa.Float(), nullable=True),
            sa.Column("final_damage", sa.Float(), nullable=True),
            sa.Column("armor_raw", sa.Float(), nullable=True),
            sa.Column("armor_effective", sa.Float(), nullable=True),
            sa.Column("armor_ignored", sa.Float(), nullable=True),
            sa.Column("phys_res_raw", sa.Float(), nullable=True),
            sa.Column("phys_res_effective", sa.Float(), nullable=True),
            sa.Column("physical_suppression", sa.Float(), nullable=True),
            sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("damage_trace", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("trigger_attempts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("mutations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("equipment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_once("ix_combat_exchange_facts_combat_id", "combat_exchange_facts", ["combat_id"])
    _create_index_once(
        "ix_combat_exchange_facts_combat_turn_seq", "combat_exchange_facts", ["combat_id", "turn", "seq"]
    )
    _create_index_once("ix_combat_exchange_facts_finished_at", "combat_exchange_facts", ["finished_at"])
    _create_index_once("ix_combat_exchange_facts_weapon", "combat_exchange_facts", ["weapon_base_id", "weapon_tier"])
    _create_index_once("ix_combat_exchange_facts_armor", "combat_exchange_facts", ["armor_class", "armor_tier"])

    tables = set(inspect(bind).get_table_names())
    if "combat_balance_rollups" not in tables:
        op.create_table(
            "combat_balance_rollups",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("bucket_grain", sa.String(length=16), nullable=False),
            sa.Column("metric_key", sa.String(length=120), nullable=False),
            sa.Column("dimensions_hash", sa.String(length=64), nullable=False),
            sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("counters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("source_count", sa.Integer(), nullable=False),
            sa.Column("aggregate_version", sa.Integer(), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "bucket_start",
                "bucket_grain",
                "metric_key",
                "dimensions_hash",
                "aggregate_version",
                name="uq_combat_balance_rollup_bucket_metric_dims_version",
            ),
        )
    _create_index_once("ix_combat_balance_rollups_bucket", "combat_balance_rollups", ["bucket_start", "bucket_grain"])
    _create_index_once("ix_combat_balance_rollups_metric", "combat_balance_rollups", ["metric_key"])
    _create_index_once("ix_combat_balance_rollups_aggregate_version", "combat_balance_rollups", ["aggregate_version"])


def downgrade() -> None:
    op.drop_table("combat_balance_rollups")
    op.drop_table("combat_exchange_facts")


def _create_index_once(index_name: str, table_name: str, columns: list[str]) -> None:
    existing = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)

"""add item generated templates

Revision ID: 0007_item_generated_templates
Revises: 0006_combat_analytics_rollups
Create Date: 2026-05-17 18:30:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0007_item_generated_templates"
down_revision: str | None = "0006_combat_analytics_rollups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

if TYPE_CHECKING:
    from collections.abc import Sequence


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "item_generated_templates" not in tables:
        op.create_table(
            "item_generated_templates",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("text_visual_hash", sa.String(length=128), nullable=False),
            sa.Column("prompt_version", sa.String(length=80), nullable=False),
            sa.Column("base_id", sa.String(length=80), nullable=False),
            sa.Column("item_type", sa.String(length=40), nullable=False),
            sa.Column("rarity", sa.String(length=30), nullable=False),
            sa.Column("rarity_tier", sa.Integer(), nullable=False),
            sa.Column("item_grade", sa.String(length=40), nullable=False),
            sa.Column("material_id", sa.String(length=80), nullable=True),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("description", sa.String(length=1000), nullable=False),
            sa.Column("image_url", sa.String(length=500), nullable=True),
            sa.Column("icon_key", sa.String(length=120), nullable=True),
            sa.Column("text_status", sa.String(length=40), nullable=False),
            sa.Column("text_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("appearance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("generation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("source_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("text_visual_hash", name="uq_item_generated_templates_text_visual_hash"),
        )
    _create_index_once("ix_item_generated_templates_text_visual_hash", "item_generated_templates", ["text_visual_hash"])
    _create_index_once("ix_item_generated_templates_prompt_version", "item_generated_templates", ["prompt_version"])
    _create_index_once("ix_item_generated_templates_base_id", "item_generated_templates", ["base_id"])
    _create_index_once("ix_item_generated_templates_rarity", "item_generated_templates", ["rarity"])
    _create_index_once("ix_item_generated_templates_rarity_tier", "item_generated_templates", ["rarity_tier"])
    _create_index_once("ix_item_generated_templates_item_grade", "item_generated_templates", ["item_grade"])
    _create_index_once("ix_item_generated_templates_material_id", "item_generated_templates", ["material_id"])
    _create_index_once("ix_item_generated_templates_text_status", "item_generated_templates", ["text_status"])

    columns = {column["name"] for column in inspect(bind).get_columns("item_instances")}
    if "generated_template_id" not in columns:
        op.add_column("item_instances", sa.Column("generated_template_id", sa.String(length=36), nullable=True))
        op.create_index("ix_item_instances_generated_template_id", "item_instances", ["generated_template_id"])
        op.create_foreign_key(
            "fk_item_instances_generated_template_id",
            "item_instances",
            "item_generated_templates",
            ["generated_template_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("item_instances")}
    if "generated_template_id" in columns:
        op.drop_constraint("fk_item_instances_generated_template_id", "item_instances", type_="foreignkey")
        op.drop_index("ix_item_instances_generated_template_id", table_name="item_instances")
        op.drop_column("item_instances", "generated_template_id")
    if "item_generated_templates" in set(inspector.get_table_names()):
        op.drop_table("item_generated_templates")


def _create_index_once(index_name: str, table_name: str, columns: list[str]) -> None:
    existing = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)

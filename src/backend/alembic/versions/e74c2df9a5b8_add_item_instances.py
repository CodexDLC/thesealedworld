"""add_item_instances

Revision ID: e74c2df9a5b8
Revises: a2f4c9b8d731
Create Date: 2026-05-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e74c2df9a5b8"
down_revision: str | Sequence[str] | None = "a2f4c9b8d731"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "item_instances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=180), nullable=False),
        sa.Column("base_id", sa.String(length=80), nullable=False),
        sa.Column("material_id", sa.String(length=80), nullable=True),
        sa.Column("item_type", sa.String(length=40), nullable=False),
        sa.Column("rarity", sa.String(length=30), nullable=False),
        sa.Column("rarity_tier", sa.Integer(), nullable=False),
        sa.Column("slot", sa.String(length=50), nullable=False),
        sa.Column("valid_slots", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("owner_type", sa.String(length=40), nullable=False),
        sa.Column("owner_id", sa.String(length=120), nullable=False),
        sa.Column("owner_slot", sa.String(length=80), nullable=True),
        sa.Column("lifecycle_status", sa.String(length=40), nullable=False),
        sa.Column("text_status", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("power", sa.Float(), nullable=False),
        sa.Column("durability_max", sa.Float(), nullable=False),
        sa.Column("damage_spread", sa.Float(), nullable=False),
        sa.Column("implicit_bonuses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("bonuses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("triggers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("affix_bundle_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("narrative_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_item_instances_base_id", "item_instances", ["base_id"])
    op.create_index("ix_item_instances_lifecycle_status", "item_instances", ["lifecycle_status"])
    op.create_index("ix_item_instances_material_id", "item_instances", ["material_id"])
    op.create_index("ix_item_instances_owner_id", "item_instances", ["owner_id"])
    op.create_index("ix_item_instances_owner_type", "item_instances", ["owner_type"])
    op.create_index("ix_item_instances_rarity", "item_instances", ["rarity"])
    op.create_index("ix_item_instances_rarity_tier", "item_instances", ["rarity_tier"])
    op.create_index("ix_item_instances_template_id", "item_instances", ["template_id"])
    op.create_index("ix_item_instances_text_status", "item_instances", ["text_status"])


def downgrade() -> None:
    op.drop_index("ix_item_instances_text_status", table_name="item_instances")
    op.drop_index("ix_item_instances_template_id", table_name="item_instances")
    op.drop_index("ix_item_instances_rarity_tier", table_name="item_instances")
    op.drop_index("ix_item_instances_rarity", table_name="item_instances")
    op.drop_index("ix_item_instances_owner_type", table_name="item_instances")
    op.drop_index("ix_item_instances_owner_id", table_name="item_instances")
    op.drop_index("ix_item_instances_material_id", table_name="item_instances")
    op.drop_index("ix_item_instances_lifecycle_status", table_name="item_instances")
    op.drop_index("ix_item_instances_base_id", table_name="item_instances")
    op.drop_table("item_instances")


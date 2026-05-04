"""compact_item_storage_schema

Revision ID: f01d2a4c3b9e
Revises: e74c2df9a5b8
Create Date: 2026-05-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f01d2a4c3b9e"
down_revision: str | Sequence[str] | None = "e74c2df9a5b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "item_instances",
        sa.Column("mechanics", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )
    op.add_column(
        "item_instances",
        sa.Column("appearance", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )
    op.add_column(
        "item_instances",
        sa.Column("generation", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )

    op.execute(
        """
        UPDATE item_instances
        SET
          mechanics = jsonb_build_object(
            'template_id', template_id,
            'slot', slot,
            'valid_slots', valid_slots,
            'power', power,
            'durability_current', durability_max,
            'durability_max', durability_max,
            'damage_spread', damage_spread,
            'implicit_bonuses', implicit_bonuses,
            'bonuses', bonuses,
            'triggers', triggers
          ),
          appearance = jsonb_build_object(
            'width_cells', COALESCE((metadata->>'width_cells')::int, 1),
            'height_cells', COALESCE((metadata->>'height_cells')::int, 1),
            'volume_units', COALESCE((metadata->>'volume_units')::int, 1),
            'icon_key', metadata->>'icon_key'
          ),
          generation = jsonb_build_object(
            'material_id', material_id,
            'affix_bundle_ids', affix_bundle_ids,
            'narrative_tags', narrative_tags,
            'source', metadata->>'source',
            'damage_type', metadata->>'damage_type',
            'defense_type', metadata->>'defense_type'
          )
        """
    )

    op.create_table(
        "item_placements",
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("holder_type", sa.String(length=40), nullable=False),
        sa.Column("holder_id", sa.String(length=120), nullable=False),
        sa.Column("storage_type", sa.String(length=60), nullable=False),
        sa.Column("slot", sa.String(length=80), nullable=True),
        sa.Column("position_index", sa.Integer(), nullable=True),
        sa.Column("locked_by", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["item_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.execute(
        """
        INSERT INTO item_placements (item_id, holder_type, holder_id, storage_type, slot)
        SELECT id, owner_type, owner_id, 'storage', owner_slot
        FROM item_instances
        """
    )
    op.create_index("ix_item_placements_holder_type", "item_placements", ["holder_type"])
    op.create_index("ix_item_placements_holder_id", "item_placements", ["holder_id"])
    op.create_index("ix_item_placements_storage_type", "item_placements", ["storage_type"])

    op.create_table(
        "resource_balances",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("holder_type", sa.String(length=40), nullable=False),
        sa.Column("holder_id", sa.String(length=120), nullable=False),
        sa.Column("storage_type", sa.String(length=60), nullable=False),
        sa.Column("resource_key", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("locked_amount", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("holder_type", "holder_id", "storage_type", "resource_key", name="uq_resource_balance_place"),
    )
    op.create_index("ix_resource_balances_holder_type", "resource_balances", ["holder_type"])
    op.create_index("ix_resource_balances_holder_id", "resource_balances", ["holder_id"])
    op.create_index("ix_resource_balances_storage_type", "resource_balances", ["storage_type"])
    op.create_index("ix_resource_balances_resource_key", "resource_balances", ["resource_key"])

    op.create_table(
        "item_origins",
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("origin_type", sa.String(length=40), nullable=False),
        sa.Column("origin_ref", sa.String(length=160), nullable=True),
        sa.Column("seed", sa.String(length=120), nullable=True),
        sa.Column("request_hash", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["item_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_index("ix_item_origins_origin_type", "item_origins", ["origin_type"])
    op.create_index("ix_item_origins_origin_ref", "item_origins", ["origin_ref"])
    op.create_index("ix_item_origins_request_hash", "item_origins", ["request_hash"])
    op.create_index("ix_item_origins_correlation_id", "item_origins", ["correlation_id"])

    op.create_table(
        "item_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("from_holder_type", sa.String(length=40), nullable=True),
        sa.Column("from_holder_id", sa.String(length=120), nullable=True),
        sa.Column("from_storage_type", sa.String(length=60), nullable=True),
        sa.Column("to_holder_type", sa.String(length=40), nullable=True),
        sa.Column("to_holder_id", sa.String(length=120), nullable=True),
        sa.Column("to_storage_type", sa.String(length=60), nullable=True),
        sa.Column("reason", sa.String(length=60), nullable=False),
        sa.Column("correlation_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_item_transactions_item_id", "item_transactions", ["item_id"])
    op.create_index("ix_item_transactions_reason", "item_transactions", ["reason"])
    op.create_index("ix_item_transactions_correlation_id", "item_transactions", ["correlation_id"])

    op.create_table(
        "resource_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("resource_key", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("from_holder_type", sa.String(length=40), nullable=True),
        sa.Column("from_holder_id", sa.String(length=120), nullable=True),
        sa.Column("from_storage_type", sa.String(length=60), nullable=True),
        sa.Column("to_holder_type", sa.String(length=40), nullable=True),
        sa.Column("to_holder_id", sa.String(length=120), nullable=True),
        sa.Column("to_storage_type", sa.String(length=60), nullable=True),
        sa.Column("reason", sa.String(length=60), nullable=False),
        sa.Column("correlation_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_transactions_resource_key", "resource_transactions", ["resource_key"])
    op.create_index("ix_resource_transactions_reason", "resource_transactions", ["reason"])
    op.create_index("ix_resource_transactions_correlation_id", "resource_transactions", ["correlation_id"])

    for index_name in (
        "ix_item_instances_template_id",
        "ix_item_instances_material_id",
        "ix_item_instances_owner_id",
        "ix_item_instances_owner_type",
    ):
        op.drop_index(index_name, table_name="item_instances")
    for column_name in (
        "template_id",
        "material_id",
        "slot",
        "valid_slots",
        "owner_type",
        "owner_id",
        "owner_slot",
        "power",
        "durability_max",
        "damage_spread",
        "implicit_bonuses",
        "bonuses",
        "triggers",
        "affix_bundle_ids",
        "narrative_tags",
    ):
        op.drop_column("item_instances", column_name)


def downgrade() -> None:
    raise RuntimeError("Downgrade for compact item storage is not supported in dev migration.")


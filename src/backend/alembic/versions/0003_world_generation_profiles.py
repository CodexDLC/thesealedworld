"""world generation profiles

Revision ID: 0003_world_generation_profiles
Revises: 0002_generation_ai_tasks
Create Date: 2026-05-15 14:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_world_generation_profiles"
down_revision: str | Sequence[str] | None = "0002_generation_ai_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "world_regions",
        sa.Column("biome_id", sa.String(length=50), server_default="wasteland", nullable=False),
        if_not_exists=True,
    )
    op.add_column(
        "world_regions",
        sa.Column("region_archetype", sa.String(length=80), server_default="wild_region", nullable=False),
        if_not_exists=True,
    )
    op.add_column(
        "world_regions",
        sa.Column("tier_min", sa.Integer(), server_default="0", nullable=False),
        if_not_exists=True,
    )
    op.add_column(
        "world_regions",
        sa.Column("tier_max", sa.Integer(), server_default="0", nullable=False),
        if_not_exists=True,
    )
    op.add_column(
        "world_regions",
        sa.Column("navigation_profile_id", sa.String(length=80), server_default="open_frontier", nullable=False),
        if_not_exists=True,
    )
    op.add_column(
        "world_regions",
        sa.Column("biome_mix", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        if_not_exists=True,
    )
    op.add_column(
        "world_regions",
        sa.Column(
            "population_profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        if_not_exists=True,
    )
    op.add_column(
        "world_regions",
        sa.Column(
            "anchor_influence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        if_not_exists=True,
    )
    op.add_column(
        "world_regions",
        sa.Column("is_locked_frontier", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        if_not_exists=True,
    )

    op.add_column(
        "world_zones",
        sa.Column("zone_archetype", sa.String(length=80), server_default="wild_core", nullable=False),
        if_not_exists=True,
    )
    op.add_column(
        "world_zones",
        sa.Column("navigation_profile_id", sa.String(length=80), server_default="open_frontier", nullable=False),
        if_not_exists=True,
    )
    op.add_column(
        "world_zones",
        sa.Column("landmark_profile", sa.String(length=80), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "world_zones",
        sa.Column(
            "population_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        if_not_exists=True,
    )

    op.add_column(
        "world_grid",
        sa.Column("navigation_profile_id", sa.String(length=80), server_default="open_frontier", nullable=False),
        if_not_exists=True,
    )
    op.add_column(
        "world_grid",
        sa.Column("buildable_kind", sa.String(length=80), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "world_grid",
        sa.Column("landmark_profile", sa.String(length=80), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "world_grid",
        sa.Column(
            "movement_profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        if_not_exists=True,
    )

    for table, columns in {
        "world_regions": (
            "biome_id",
            "region_archetype",
            "tier_min",
            "tier_max",
            "navigation_profile_id",
            "is_locked_frontier",
        ),
        "world_zones": ("zone_archetype", "navigation_profile_id", "landmark_profile"),
        "world_grid": ("navigation_profile_id", "buildable_kind", "landmark_profile"),
    }.items():
        for column in columns:
            op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False, if_not_exists=True)


def downgrade() -> None:
    for table, columns in {
        "world_grid": ("movement_profile", "landmark_profile", "buildable_kind", "navigation_profile_id"),
        "world_zones": ("population_tags", "landmark_profile", "navigation_profile_id", "zone_archetype"),
        "world_regions": (
            "is_locked_frontier",
            "anchor_influence",
            "population_profile",
            "biome_mix",
            "navigation_profile_id",
            "tier_max",
            "tier_min",
            "region_archetype",
            "biome_id",
        ),
    }.items():
        for column in columns:
            op.drop_column(table, column, if_exists=True)

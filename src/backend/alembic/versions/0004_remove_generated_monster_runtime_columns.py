"""remove generated monster runtime columns

Revision ID: 0004_monster_runtime_cols
Revises: 0003_world_generation_profiles
Create Date: 2026-05-15 21:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_monster_runtime_cols"
down_revision: str | Sequence[str] | None = "0003_world_generation_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in ("faction_key", "side_key", "group_key"):
        op.drop_column("generated_monsters", column, if_exists=True)

    op.drop_column("generated_clans", "location_id", if_exists=True)


def downgrade() -> None:
    op.add_column("generated_clans", sa.Column("location_id", sa.String(), nullable=True))
    op.create_index("ix_generated_clans_location_id", "generated_clans", ["location_id"], unique=False)

    for column in ("faction_key", "side_key", "group_key"):
        op.add_column("generated_monsters", sa.Column(column, sa.String(), nullable=True))
        op.create_index(f"ix_generated_monsters_{column}", "generated_monsters", [column], unique=False)

"""add_monster_combat_seed

Revision ID: b18f6d2a9c43
Revises: f01d2a4c3b9e
Create Date: 2026-05-06 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b18f6d2a9c43"
down_revision: str | Sequence[str] | None = "f01d2a4c3b9e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generated_monsters",
        sa.Column("combat_seed", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("generated_monsters", "combat_seed")

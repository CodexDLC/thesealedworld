"""game schema baseline

Revision ID: 0001_game_schema_baseline
Revises:
Create Date: 2026-05-14 23:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.backend.core.database import Base
from src.backend.core.database import model_imports as model_imports  # noqa: F401

revision: str = "0001_game_schema_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS chat"))
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
    op.execute(sa.text("DROP SCHEMA IF EXISTS chat CASCADE"))

"""site auth legacy baseline

Revision ID: 8f240ce57add
Revises:
Create Date: 2026-05-17 18:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.frontend.core.database import Base
from src.frontend.core.database import model_imports as model_imports  # noqa: F401

revision: str = "8f240ce57add"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS site"))
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())

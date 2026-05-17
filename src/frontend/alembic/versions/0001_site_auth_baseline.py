"""site auth baseline

Revision ID: 0001_site_auth_baseline
Revises:
Create Date: 2026-05-17 18:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.frontend.core.database import Base
from src.frontend.core.database import model_imports as model_imports  # noqa: F401

revision: str = "0001_site_auth_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS site"))
    Base.metadata.create_all(bind=op.get_bind())
    op.add_column(
        "auth_users",
        sa.Column("tester_status", sa.String(length=20), nullable=False, server_default="none"),
        schema="site",
        if_not_exists=True,
    )
    op.add_column(
        "auth_users",
        sa.Column("tester_approved_at", sa.DateTime(timezone=True), nullable=True),
        schema="site",
        if_not_exists=True,
    )
    op.alter_column("auth_users", "tester_status", server_default=None, schema="site")


def downgrade() -> None:
    op.drop_table("auth_refresh_tokens", schema="site", if_exists=True)
    op.drop_table("auth_users", schema="site", if_exists=True)

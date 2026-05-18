"""site auth tester fields

Revision ID: 0002_site_auth_tester_fields
Revises: 8f240ce57add
Create Date: 2026-05-17 18:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_site_auth_tester_fields"
down_revision: str | Sequence[str] | None = "8f240ce57add"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
    op.drop_column("auth_users", "tester_approved_at", schema="site", if_exists=True)
    op.drop_column("auth_users", "tester_status", schema="site", if_exists=True)

"""player daily activity

Revision ID: 0003_player_daily_activity
Revises: 0002_site_auth_tester_fields
Create Date: 2026-05-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_player_daily_activity"
down_revision: str | None = "0002_site_auth_tester_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS site")

    if not _table_exists("player_daily_activity"):
        op.create_table(
            "player_daily_activity",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("player_id", sa.UUID, nullable=False),
            sa.Column("date", sa.Date, nullable=False),
            sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("player_id", "date", name="uq_player_daily_activity"),
            schema="site",
        )
        op.create_index("ix_site_player_daily_activity_date", "player_daily_activity", ["date"], schema="site")


def downgrade() -> None:
    op.drop_index("ix_site_player_daily_activity_date", table_name="player_daily_activity", schema="site")
    op.drop_table("player_daily_activity", schema="site")


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema="site")

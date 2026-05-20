"""add articles table

Revision ID: 0002_add_articles_table
Revises: 0001_site_schema_baseline
Create Date: 2026-05-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_articles_table"
down_revision: str | Sequence[str] | None = "0001_site_schema_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(200), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("preview", sa.String(400), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("cover_image", sa.String(500), nullable=True),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="site",
    )


def downgrade() -> None:
    op.drop_table("articles", schema="site")

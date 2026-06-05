"""security baseline: hashed refresh tokens

Revision ID: 0002_security_baseline
Revises: 0001_site_schema_baseline
Create Date: 2026-06-06 00:00:00.000000
"""

import hashlib
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_security_baseline"
down_revision: str | Sequence[str] | None = "0001_site_schema_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column(
        "auth_refresh_tokens",
        sa.Column("token_hash", sa.String(length=64), nullable=True),
        schema="site",
    )

    rows = bind.execute(sa.text("SELECT id, token FROM site.auth_refresh_tokens")).fetchall()
    for row_id, token in rows:
        if not token:
            continue
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        bind.execute(
            sa.text("UPDATE site.auth_refresh_tokens SET token_hash = :digest WHERE id = :row_id"),
            {"digest": digest, "row_id": row_id},
        )

    bind.execute(sa.text("DELETE FROM site.auth_refresh_tokens WHERE token_hash IS NULL"))

    op.alter_column(
        "auth_refresh_tokens",
        "token_hash",
        existing_type=sa.String(length=64),
        nullable=False,
        schema="site",
    )
    op.create_index(
        "ix_auth_refresh_tokens_token_hash",
        "auth_refresh_tokens",
        ["token_hash"],
        unique=True,
        schema="site",
    )

    bind.execute(sa.text("DROP INDEX IF EXISTS site.ix_auth_refresh_tokens_token"))
    bind.execute(sa.text("ALTER TABLE site.auth_refresh_tokens DROP COLUMN IF EXISTS token"))


def downgrade() -> None:
    op.add_column(
        "auth_refresh_tokens",
        sa.Column("token", sa.String(length=128), nullable=True),
        schema="site",
    )
    op.create_index(
        "ix_auth_refresh_tokens_token",
        "auth_refresh_tokens",
        ["token"],
        unique=True,
        schema="site",
    )
    op.drop_index("ix_auth_refresh_tokens_token_hash", table_name="auth_refresh_tokens", schema="site")
    op.drop_column("auth_refresh_tokens", "token_hash", schema="site")

"""email verification tokens and verified_at column

Revision ID: 0004_email_verification
Revises: 0003_referrals
Create Date: 2026-06-06 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_email_verification"
down_revision: str | Sequence[str] | None = "0003_referrals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "auth_users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        schema="site",
    )

    op.create_table(
        "auth_email_verification_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("site.auth_users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("new_email", sa.String(length=320), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="site",
    )
    op.create_index(
        "ix_auth_email_verification_tokens_token_hash",
        "auth_email_verification_tokens",
        ["token_hash"],
        unique=True,
        schema="site",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_email_verification_tokens_token_hash",
        table_name="auth_email_verification_tokens",
        schema="site",
    )
    op.drop_table("auth_email_verification_tokens", schema="site")
    op.drop_column("auth_users", "email_verified_at", schema="site")

"""referrals: per-user code, referrer link, reward log

Revision ID: 0003_referrals
Revises: 0002_security_baseline
Create Date: 2026-06-06 00:01:00.000000
"""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_referrals"
down_revision: str | Sequence[str] | None = "0002_security_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # pragma: allowlist secret


def _generate_code() -> str:
    return "SEAL-" + "".join(secrets.choice(_ALPHABET) for _ in range(8))


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column(
        "auth_users",
        sa.Column("referral_code", sa.String(length=16), nullable=True),
        schema="site",
    )
    op.add_column(
        "auth_users",
        sa.Column("referred_by_id", sa.UUID(), nullable=True),
        schema="site",
    )

    # Backfill referral_code for existing users; codes are short and the alphabet is large,
    # but we still loop on rare collisions.
    rows = bind.execute(sa.text("SELECT id FROM site.auth_users WHERE referral_code IS NULL")).fetchall()
    for (user_id,) in rows:
        while True:
            code = _generate_code()
            existing = bind.execute(
                sa.text("SELECT 1 FROM site.auth_users WHERE referral_code = :code"),
                {"code": code},
            ).fetchone()
            if existing is None:
                bind.execute(
                    sa.text("UPDATE site.auth_users SET referral_code = :code WHERE id = :uid"),
                    {"code": code, "uid": user_id},
                )
                break

    op.alter_column(
        "auth_users",
        "referral_code",
        existing_type=sa.String(length=16),
        nullable=False,
        schema="site",
    )
    op.create_index(
        "ix_auth_users_referral_code",
        "auth_users",
        ["referral_code"],
        unique=True,
        schema="site",
    )
    op.create_index(
        "ix_auth_users_referred_by_id",
        "auth_users",
        ["referred_by_id"],
        schema="site",
    )
    op.create_foreign_key(
        "fk_auth_users_referred_by_id",
        "auth_users",
        "auth_users",
        ["referred_by_id"],
        ["id"],
        source_schema="site",
        referent_schema="site",
        ondelete="SET NULL",
    )

    op.create_table(
        "auth_referral_rewards",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "referrer_id",
            sa.UUID(),
            sa.ForeignKey("site.auth_users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "referee_id",
            sa.UUID(),
            sa.ForeignKey("site.auth_users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("referrer_id", "referee_id", "kind", name="uq_auth_referral_rewards_event"),
        schema="site",
    )


def downgrade() -> None:
    op.drop_table("auth_referral_rewards", schema="site")
    op.drop_constraint("fk_auth_users_referred_by_id", "auth_users", schema="site", type_="foreignkey")
    op.drop_index("ix_auth_users_referred_by_id", table_name="auth_users", schema="site")
    op.drop_index("ix_auth_users_referral_code", table_name="auth_users", schema="site")
    op.drop_column("auth_users", "referred_by_id", schema="site")
    op.drop_column("auth_users", "referral_code", schema="site")

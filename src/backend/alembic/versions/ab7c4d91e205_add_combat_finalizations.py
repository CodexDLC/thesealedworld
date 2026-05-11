"""add_combat_finalizations

Revision ID: ab7c4d91e205
Revises: c6b5a2d4e901
Create Date: 2026-05-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ab7c4d91e205"
down_revision: str | Sequence[str] | None = "c6b5a2d4e901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "combat_finalizations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("combat_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.Column("battle_type", sa.String(length=40), nullable=True),
        sa.Column("location_id", sa.String(length=120), nullable=True),
        sa.Column("arena_session_id", sa.String(length=64), nullable=True),
        sa.Column("winner_team", sa.String(length=80), nullable=True),
        sa.Column(
            "participant_char_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("persisted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "finalization",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("analytics", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("reward_hooks", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_combat_finalizations_combat_id"), "combat_finalizations", ["combat_id"], unique=True)
    op.create_index(op.f("ix_combat_finalizations_status"), "combat_finalizations", ["status"], unique=False)
    op.create_index(op.f("ix_combat_finalizations_source"), "combat_finalizations", ["source"], unique=False)
    op.create_index(op.f("ix_combat_finalizations_battle_type"), "combat_finalizations", ["battle_type"], unique=False)
    op.create_index(op.f("ix_combat_finalizations_location_id"), "combat_finalizations", ["location_id"], unique=False)
    op.create_index(
        op.f("ix_combat_finalizations_arena_session_id"),
        "combat_finalizations",
        ["arena_session_id"],
        unique=False,
    )
    op.create_index(op.f("ix_combat_finalizations_winner_team"), "combat_finalizations", ["winner_team"], unique=False)
    op.create_index("ix_combat_finalizations_finished_at", "combat_finalizations", ["finished_at"], unique=False)
    op.create_index(
        "ix_combat_finalizations_participant_char_ids",
        "combat_finalizations",
        ["participant_char_ids"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_combat_finalizations_participant_char_ids", table_name="combat_finalizations")
    op.drop_index("ix_combat_finalizations_finished_at", table_name="combat_finalizations")
    op.drop_index(op.f("ix_combat_finalizations_winner_team"), table_name="combat_finalizations")
    op.drop_index(op.f("ix_combat_finalizations_arena_session_id"), table_name="combat_finalizations")
    op.drop_index(op.f("ix_combat_finalizations_location_id"), table_name="combat_finalizations")
    op.drop_index(op.f("ix_combat_finalizations_battle_type"), table_name="combat_finalizations")
    op.drop_index(op.f("ix_combat_finalizations_source"), table_name="combat_finalizations")
    op.drop_index(op.f("ix_combat_finalizations_status"), table_name="combat_finalizations")
    op.drop_index(op.f("ix_combat_finalizations_combat_id"), table_name="combat_finalizations")
    op.drop_table("combat_finalizations")

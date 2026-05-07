"""arena_ranking

Revision ID: c6b5a2d4e901
Revises: b18f6d2a9c43
Create Date: 2026-05-06 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c6b5a2d4e901"
down_revision: str | Sequence[str] | None = "b18f6d2a9c43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEAGUES = (
    (1, "rookie", "Rookie", 0, 1199),
    (2, "fighter", "Fighter", 1200, 1399),
    (3, "challenger", "Challenger", 1400, 1599),
    (4, "veteran", "Veteran", 1600, 1799),
    (5, "elite", "Elite", 1800, 2099),
    (6, "legend", "Legend", 2100, None),
)


def upgrade() -> None:
    op.create_table(
        "arena_seasons",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("reward_pool_total", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "arena_teams",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("leader_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=48), nullable=False),
        sa.Column("size", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["leader_id"], ["characters.character_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("leader_id", "name", name="uq_arena_teams_leader_name"),
    )
    op.create_index("ix_arena_teams_leader_id", "arena_teams", ["leader_id"])

    op.create_table(
        "arena_leagues",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tier", sa.SmallInteger(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("min_rating", sa.Integer(), nullable=False),
        sa.Column("max_rating", sa.Integer(), nullable=True),
        sa.Column("season_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["season_id"], ["arena_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "tier", name="uq_arena_leagues_season_tier"),
    )
    op.create_index("ix_arena_leagues_season_id", "arena_leagues", ["season_id"])

    op.create_table(
        "arena_team_members",
        sa.Column("team_id", sa.BigInteger(), nullable=False),
        sa.Column("char_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="member", nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["char_id"], ["characters.character_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["arena_teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("team_id", "char_id"),
    )

    op.create_table(
        "arena_ratings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(length=16), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("mode_size", sa.SmallInteger(), nullable=False),
        sa.Column("season_id", sa.BigInteger(), nullable=False),
        sa.Column("rating", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("peak_rating", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("wins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("losses", sa.Integer(), server_default="0", nullable=False),
        sa.Column("draws", sa.Integer(), server_default="0", nullable=False),
        sa.Column("league_tier", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("matches_played", sa.Integer(), server_default="0", nullable=False),
        sa.Column("placement_left", sa.SmallInteger(), server_default="5", nullable=False),
        sa.Column("last_match_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["season_id"], ["arena_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            "mode_size",
            "season_id",
            name="uq_arena_ratings_entity_mode_season",
        ),
    )
    op.create_index(
        "ix_arena_ratings_leaderboard",
        "arena_ratings",
        ["season_id", "mode_size", sa.text("rating DESC")],
    )

    op.create_table(
        "arena_matches",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("combat_id", sa.String(length=64), nullable=True),
        sa.Column("arena_session_id", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("mode_size", sa.SmallInteger(), nullable=False),
        sa.Column("season_id", sa.BigInteger(), nullable=False),
        sa.Column("team_a_entity_type", sa.String(length=16), nullable=False),
        sa.Column("team_a_entity_id", sa.BigInteger(), nullable=False),
        sa.Column("team_b_entity_type", sa.String(length=16), nullable=False),
        sa.Column("team_b_entity_id", sa.BigInteger(), nullable=False),
        sa.Column("team_a_member_ids", postgresql.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column("team_b_member_ids", postgresql.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column("team_a_gs_locked", sa.Integer(), nullable=False),
        sa.Column("team_b_gs_locked", sa.Integer(), nullable=False),
        sa.Column("team_a_rating_before", sa.Integer(), nullable=True),
        sa.Column("team_a_rating_after", sa.Integer(), nullable=True),
        sa.Column("team_b_rating_before", sa.Integer(), nullable=True),
        sa.Column("team_b_rating_after", sa.Integer(), nullable=True),
        sa.Column("winner", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["season_id"], ["arena_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_arena_matches_arena_session_id", "arena_matches", ["arena_session_id"])
    op.create_index("ix_arena_matches_combat_id", "arena_matches", ["combat_id"])
    op.create_index("ix_arena_matches_completed_at", "arena_matches", ["completed_at"])
    op.create_index("ix_arena_matches_season_id", "arena_matches", ["season_id"])
    op.create_index("ix_arena_matches_team_a_members", "arena_matches", ["team_a_member_ids"], postgresql_using="gin")
    op.create_index("ix_arena_matches_team_b_members", "arena_matches", ["team_b_member_ids"], postgresql_using="gin")

    op.create_table(
        "arena_brawl_xp",
        sa.Column("char_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.BigInteger(), nullable=False),
        sa.Column("xp", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("matches_played", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["char_id"], ["characters.character_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["arena_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("char_id", "season_id"),
    )

    op.create_table(
        "arena_season_rewards",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("season_id", sa.BigInteger(), nullable=False),
        sa.Column("entity_type", sa.String(length=16), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(["season_id"], ["arena_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_arena_season_rewards_season_id", "arena_season_rewards", ["season_id"])

    op.bulk_insert(
        sa.table(
            "arena_leagues",
            sa.column("tier", sa.SmallInteger()),
            sa.column("code", sa.String()),
            sa.column("name", sa.String()),
            sa.column("min_rating", sa.Integer()),
            sa.column("max_rating", sa.Integer()),
            sa.column("season_id", sa.BigInteger()),
        ),
        [
            {
                "tier": tier,
                "code": code,
                "name": name,
                "min_rating": min_rating,
                "max_rating": max_rating,
                "season_id": None,
            }
            for tier, code, name, min_rating, max_rating in LEAGUES
        ],
    )
    op.execute(
        """
        INSERT INTO arena_seasons (name, started_at, ends_at, status, reward_pool_total)
        VALUES (
          'Season 1',
          timezone('utc', now()),
          timezone('utc', now()) + interval '3 months',
          'active',
          0
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_arena_season_rewards_season_id", table_name="arena_season_rewards")
    op.drop_table("arena_season_rewards")
    op.drop_table("arena_brawl_xp")
    op.drop_index("ix_arena_matches_team_b_members", table_name="arena_matches")
    op.drop_index("ix_arena_matches_team_a_members", table_name="arena_matches")
    op.drop_index("ix_arena_matches_season_id", table_name="arena_matches")
    op.drop_index("ix_arena_matches_completed_at", table_name="arena_matches")
    op.drop_index("ix_arena_matches_combat_id", table_name="arena_matches")
    op.drop_index("ix_arena_matches_arena_session_id", table_name="arena_matches")
    op.drop_table("arena_matches")
    op.drop_index("ix_arena_ratings_leaderboard", table_name="arena_ratings")
    op.drop_table("arena_ratings")
    op.drop_table("arena_team_members")
    op.drop_index("ix_arena_leagues_season_id", table_name="arena_leagues")
    op.drop_table("arena_leagues")
    op.drop_index("ix_arena_teams_leader_id", table_name="arena_teams")
    op.drop_table("arena_teams")
    op.drop_table("arena_seasons")

"""add combat ai simulation run storage

Revision ID: 0003_combat_ai_simulation_runs
Revises: 0002_rift_portal_keys
Create Date: 2026-05-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_combat_ai_simulation_runs"
down_revision: str | Sequence[str] | None = "0002_rift_portal_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS combat_ai_simulation_runs (
                id VARCHAR(36) NOT NULL,
                run_kind VARCHAR(40) NOT NULL,
                scenario_key VARCHAR(120) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'completed',
                policy_ref VARCHAR(240),
                seed INTEGER NOT NULL DEFAULT 0,
                max_rounds INTEGER NOT NULL DEFAULT 5,
                rounds_completed INTEGER NOT NULL DEFAULT 0,
                winner VARCHAR(40),
                reward DOUBLE PRECISION,
                telemetry JSONB NOT NULL DEFAULT '{}'::jsonb,
                report_text TEXT NOT NULL DEFAULT '',
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                schema_version INTEGER NOT NULL DEFAULT 1,
                CONSTRAINT pk_combat_ai_simulation_runs PRIMARY KEY (id)
            )
            """
        )
    )
    for statement in (
        "CREATE INDEX IF NOT EXISTS ix_combat_ai_simulation_runs_created_at ON combat_ai_simulation_runs (created_at)",
        "CREATE INDEX IF NOT EXISTS ix_combat_ai_simulation_runs_policy_ref ON combat_ai_simulation_runs (policy_ref)",
        "CREATE INDEX IF NOT EXISTS ix_combat_ai_simulation_runs_run_kind ON combat_ai_simulation_runs (run_kind)",
        "CREATE INDEX IF NOT EXISTS ix_combat_ai_simulation_runs_scenario_key ON combat_ai_simulation_runs (scenario_key)",
        "CREATE INDEX IF NOT EXISTS ix_combat_ai_simulation_runs_scenario_status ON combat_ai_simulation_runs (scenario_key, status)",
        "CREATE INDEX IF NOT EXISTS ix_combat_ai_simulation_runs_status ON combat_ai_simulation_runs (status)",
        "CREATE INDEX IF NOT EXISTS ix_combat_ai_simulation_runs_winner ON combat_ai_simulation_runs (winner)",
    ):
        op.execute(sa.text(statement))


def downgrade() -> None:
    for index_name in (
        "ix_combat_ai_simulation_runs_winner",
        "ix_combat_ai_simulation_runs_status",
        "ix_combat_ai_simulation_runs_scenario_status",
        "ix_combat_ai_simulation_runs_scenario_key",
        "ix_combat_ai_simulation_runs_run_kind",
        "ix_combat_ai_simulation_runs_policy_ref",
        "ix_combat_ai_simulation_runs_created_at",
    ):
        op.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))
    op.execute(sa.text("DROP TABLE IF EXISTS combat_ai_simulation_runs"))

"""add rift portal keys

Revision ID: 0002_rift_portal_keys
Revises: 0001_game_schema_baseline
Create Date: 2026-05-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_rift_portal_keys"
down_revision: str | Sequence[str] | None = "0001_game_schema_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS rift_portal_keys (
                portal_id VARCHAR(128) NOT NULL,
                portal_key VARCHAR(128) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                source VARCHAR(64) NOT NULL DEFAULT 'unknown',
                source_ref VARCHAR(255),
                rift_key VARCHAR(96),
                entry_reason VARCHAR(80),
                entry_mode VARCHAR(64) NOT NULL DEFAULT 'direct',
                owner_type VARCHAR(32) NOT NULL DEFAULT 'character',
                owner_id VARCHAR(160) NOT NULL,
                participant_scope VARCHAR(32) NOT NULL DEFAULT 'solo',
                rift_session_id VARCHAR(128),
                rift_instance_id VARCHAR(128),
                service_id VARCHAR(128),
                source_location_id VARCHAR(128),
                exit_target_state VARCHAR(64),
                exit_location_id VARCHAR(128),
                expires_at TIMESTAMP WITH TIME ZONE,
                closed_at TIMESTAMP WITH TIME ZONE,
                archived_at TIMESTAMP WITH TIME ZONE,
                entry_context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                exit_policy_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                runtime_refs_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                context JSONB NOT NULL DEFAULT '{}'::jsonb,
                source_context JSONB NOT NULL DEFAULT '{}'::jsonb,
                schema_version INTEGER NOT NULL DEFAULT 1,
                CONSTRAINT pk_rift_portal_keys PRIMARY KEY (portal_id),
                CONSTRAINT uq_rift_portal_keys_portal_key UNIQUE (portal_key)
            )
            """
        )
    )
    for statement in (
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_archived_at ON rift_portal_keys (archived_at)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_closed_at ON rift_portal_keys (closed_at)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_entry_reason ON rift_portal_keys (entry_reason)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_exit_location_id ON rift_portal_keys (exit_location_id)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_expires_at ON rift_portal_keys (expires_at)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_owner_id ON rift_portal_keys (owner_id)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_owner_type ON rift_portal_keys (owner_type)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_participant_scope ON rift_portal_keys (participant_scope)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_portal_key ON rift_portal_keys (portal_key)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_rift_instance_id ON rift_portal_keys (rift_instance_id)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_rift_key ON rift_portal_keys (rift_key)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_rift_session_id ON rift_portal_keys (rift_session_id)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_service_id ON rift_portal_keys (service_id)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_source ON rift_portal_keys (source)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_source_location_id ON rift_portal_keys (source_location_id)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_source_ref ON rift_portal_keys (source_ref)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_keys_status ON rift_portal_keys (status)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_owner_status ON rift_portal_keys (owner_type, owner_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_rift_portal_source_ref ON rift_portal_keys (source, source_ref)",
    ):
        op.execute(sa.text(statement))


def downgrade() -> None:
    for index_name in (
        "ix_rift_portal_source_ref",
        "ix_rift_portal_owner_status",
        "ix_rift_portal_keys_status",
        "ix_rift_portal_keys_source_ref",
        "ix_rift_portal_keys_source_location_id",
        "ix_rift_portal_keys_source",
        "ix_rift_portal_keys_service_id",
        "ix_rift_portal_keys_rift_session_id",
        "ix_rift_portal_keys_rift_key",
        "ix_rift_portal_keys_rift_instance_id",
        "ix_rift_portal_keys_portal_key",
        "ix_rift_portal_keys_participant_scope",
        "ix_rift_portal_keys_owner_type",
        "ix_rift_portal_keys_owner_id",
        "ix_rift_portal_keys_expires_at",
        "ix_rift_portal_keys_exit_location_id",
        "ix_rift_portal_keys_entry_reason",
        "ix_rift_portal_keys_closed_at",
        "ix_rift_portal_keys_archived_at",
    ):
        op.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))
    op.execute(sa.text("DROP TABLE IF EXISTS rift_portal_keys"))

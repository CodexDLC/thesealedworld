"""rename_character_attribute_keys

Revision ID: a2f4c9b8d731
Revises: d0014c57f7f6
Create Date: 2026-05-02 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2f4c9b8d731"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "d0014c57f7f6"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("character_attributes", "intelligence", new_column_name="intellect")
    op.alter_column("character_attributes", "wisdom", new_column_name="memory")
    op.alter_column("character_attributes", "men", new_column_name="mental")
    op.alter_column("character_attributes", "charisma", new_column_name="projection")
    op.alter_column("character_attributes", "luck", new_column_name="prediction")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("character_attributes", "intellect", new_column_name="intelligence")
    op.alter_column("character_attributes", "memory", new_column_name="wisdom")
    op.alter_column("character_attributes", "mental", new_column_name="men")
    op.alter_column("character_attributes", "projection", new_column_name="charisma")
    op.alter_column("character_attributes", "prediction", new_column_name="luck")

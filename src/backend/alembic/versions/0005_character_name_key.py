"""add character name key

Revision ID: 0005_character_name_key
Revises: 0004_monster_runtime_cols
Create Date: 2026-05-16 01:55:00.000000
"""

import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_character_name_key"
down_revision: str | Sequence[str] | None = "0004_monster_runtime_cols"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("name_key", sa.String(length=64), nullable=True))

    bind = op.get_bind()
    characters = sa.table(
        "characters",
        sa.column("character_id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("name_key", sa.String()),
    )

    seen: dict[str, int] = {}
    invalid: list[str] = []
    rows = bind.execute(sa.select(characters.c.character_id, characters.c.name)).mappings()
    for row in rows:
        character_id = int(row["character_id"])
        raw_name = str(row["name"] or "")
        try:
            key = _character_name_key(raw_name)
        except ValueError as exc:
            invalid.append(f"{character_id}:{exc}")
            continue
        if key in seen:
            invalid.append(f"{character_id}:duplicate normalized name with character {seen[key]}")
            continue
        seen[key] = character_id
        bind.execute(characters.update().where(characters.c.character_id == character_id).values(name_key=key))

    if invalid:
        raise RuntimeError("Cannot add characters.name_key; invalid existing names: " + ", ".join(invalid))

    op.alter_column("characters", "name_key", existing_type=sa.String(length=64), nullable=False)
    op.create_unique_constraint("uq_characters_name_key", "characters", ["name_key"])


def downgrade() -> None:
    op.drop_constraint("uq_characters_name_key", "characters", type_="unique")
    op.drop_column("characters", "name_key")


def _character_name_key(value: str) -> str:
    name = unicodedata.normalize("NFKC", value).strip()
    if len(name) < 3 or len(name) > 16:
        raise ValueError("invalid_length")
    if name.startswith("_") or name.endswith("_") or "__" in name:
        raise ValueError("invalid_underscore")

    has_latin = False
    has_cyrillic = False
    has_letter = False
    for char in name:
        if char == "_" or (char.isascii() and char.isdecimal()):
            continue
        if ("a" <= char <= "z") or ("A" <= char <= "Z"):
            has_latin = True
            has_letter = True
            continue
        if "\u0400" <= char <= "\u04ff":
            has_cyrillic = True
            has_letter = True
            continue
        raise ValueError("invalid_characters")

    if not has_letter:
        raise ValueError("letters_required")
    if has_latin and has_cyrillic:
        raise ValueError("mixed_scripts")
    return name.casefold().replace("ё", "е")

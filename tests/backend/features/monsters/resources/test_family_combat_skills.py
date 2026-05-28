from __future__ import annotations

import ast
from pathlib import Path

from src.backend.features.monsters.skill_contract import MONSTER_COMBAT_SKILL_KEYS


def test_starter_monster_variants_only_use_monster_combat_skills() -> None:
    families = [
        _load_family("rats.py"),
        _load_family("wolves.py"),
        _load_family("bandits.py"),
        _load_family("goblins.py"),
    ]
    invalid: dict[str, list[str]] = {}

    for family in families:
        keys = set()
        for variant in (family.get("variants") or {}).values():
            keys.update(variant.get("skills") or [])
        bad_keys = sorted(key for key in keys if key is not None and key not in MONSTER_COMBAT_SKILL_KEYS)
        if bad_keys:
            invalid[str(family["id"])] = bad_keys

    assert invalid == {}


def _load_family(filename: str) -> dict:
    path = Path("src/backend/features/monsters/resources/families") / filename
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.endswith("_FAMILY"):
                    return ast.literal_eval(node.value)
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id.endswith("_FAMILY")
            and node.value is not None
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"No family assignment found in {path}")

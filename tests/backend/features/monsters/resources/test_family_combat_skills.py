from __future__ import annotations

from importlib import import_module

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
    module_name = f"src.backend.features.monsters.resources.families.{filename.removesuffix('.py')}"
    module = import_module(module_name)
    for name, value in vars(module).items():
        if name.endswith("_FAMILY"):
            return dict(value)
    raise AssertionError(f"No family assignment found in {module_name}")

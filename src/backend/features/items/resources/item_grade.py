from __future__ import annotations

AFFIX_CONTAINER_RULES: dict[str, dict[str, object]] = {
    "no_grade": {"min": 0, "max": 0, "bundle_chance": 0.00, "bundle_sizes": []},
    "common": {"min": 1, "max": 1, "bundle_chance": 0.00, "bundle_sizes": []},
    "uncommon": {"min": 1, "max": 2, "bundle_chance": 0.00, "bundle_sizes": []},
    "rare": {"min": 2, "max": 3, "bundle_chance": 0.30, "bundle_sizes": [3]},
    "epic": {"min": 3, "max": 4, "bundle_chance": 0.60, "bundle_sizes": [3, 4]},
    "mythic": {"min": 4, "max": 4, "bundle_chance": 0.80, "bundle_sizes": [3, 4]},
    "legendary": {"min": 4, "max": 4, "bundle_chance": 1.00, "bundle_sizes": [3, 4]},
    "absolute": {"min": 4, "max": 4, "bundle_chance": 1.00, "bundle_sizes": [3, 4]},
    "monster_equipment_4slot": {"min": 4, "max": 4, "bundle_chance": 1.00, "bundle_sizes": [3, 4]},
}

GRADE_BY_RARITY_TIER: dict[int, str] = {
    0: "no_grade",
    1: "common",
    2: "uncommon",
    3: "rare",
    4: "epic",
    5: "mythic",
    6: "legendary",
    7: "absolute",
}

KNOWN_GRADES: list[str] = list(AFFIX_CONTAINER_RULES)

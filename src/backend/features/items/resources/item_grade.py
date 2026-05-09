from __future__ import annotations

AFFIX_CONTAINER_RULES: dict[str, dict[str, object]] = {
    "common": {"min": 0, "max": 0, "bundle_chance": 0.00, "bundle_sizes": []},
    "uncommon": {"min": 1, "max": 2, "bundle_chance": 0.00, "bundle_sizes": []},
    "rare": {"min": 2, "max": 4, "bundle_chance": 0.30, "bundle_sizes": [4]},
    "epic": {"min": 3, "max": 4, "bundle_chance": 0.60, "bundle_sizes": [3, 4]},
    "artifact": {"min": 4, "max": 4, "bundle_chance": 1.00, "bundle_sizes": [3, 4]},
}

GRADE_BY_RARITY_TIER: dict[int, str] = {
    0: "common",
    1: "uncommon",
    2: "rare",
    3: "epic",
    4: "artifact",
    5: "artifact",
    6: "artifact",
    7: "artifact",
}

KNOWN_GRADES: list[str] = list(AFFIX_CONTAINER_RULES)

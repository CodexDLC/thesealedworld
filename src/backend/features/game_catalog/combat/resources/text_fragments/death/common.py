DEATH_COMMON_PHRASES = {
    "death": {
        # --- cause: damage (generic physical kill, source omitted) ---
        "death.common.damage.fall": {
            "kind": "death",
            "text": "{target} получает {damage} урона, падает и больше не поднимается.",
            "variables": ["target", "damage"],
            "tags": ["death", "damage", "generic"],
        },
        "death.common.damage.last_stand": {
            "kind": "death",
            "text": "{target} получает {damage} урона, делает последний шаг и рушится.",
            "variables": ["target", "damage"],
            "tags": ["death", "damage", "generic"],
        },
        "death.common.damage.overkill": {
            "kind": "death",
            "text": "{target} сметён с поля боя — оверкилл на {overkill}.",
            "variables": ["target", "overkill"],
            "tags": ["death", "damage", "overkill"],
        },
        # --- cause: unknown (no source attribution — R-1) ---
        "death.common.unknown.collapses": {
            "kind": "death",
            "text": "{target} падает замертво.",
            "variables": ["target"],
            "tags": ["death", "unknown", "generic"],
        },
        "death.common.unknown.silence": {
            "kind": "death",
            "text": "{target} уходит в тишину.",
            "variables": ["target"],
            "tags": ["death", "unknown", "generic", "poetic"],
        },
    },
}

DEATH_BEAST_PHRASES = {
    "death": {
        # --- cause: damage, source known ---
        "death.beast.damage.brought_down": {
            "kind": "death",
            "text": "{source} валит {target} на землю, нанося {damage} урона.",
            "variables": ["source", "target", "damage"],
            "tags": ["death", "damage", "beast", "sourced"],
        },
        "death.beast.damage.last_breath": {
            "kind": "death",
            "text": "{target} получает {damage} урона и испускает последний вздох.",
            "variables": ["target", "damage"],
            "tags": ["death", "damage", "beast"],
        },
        "death.beast.damage.falls": {
            "kind": "death",
            "text": "{target} рушится под ударом {source}, получив {damage} урона.",
            "variables": ["target", "source", "damage"],
            "tags": ["death", "damage", "beast", "sourced"],
        },
        # --- cause: dot, effect required (R-2) ---
        "death.beast.dot.poison_end": {
            "kind": "death",
            "text": "{target} гибнет от яда {effect}.",
            "variables": ["target", "effect"],
            "tags": ["death", "dot", "beast", "effect_named", "poison"],
        },
        "death.beast.dot.withers": {
            "kind": "death",
            "text": "{target} угасает под действием {effect}.",
            "variables": ["target", "effect"],
            "tags": ["death", "dot", "beast", "effect_named"],
        },
        # --- cause: ability, ability preferred (R-3) ---
        "death.beast.ability.felled": {
            "kind": "death",
            "text": "{target} сражён {ability}.",
            "variables": ["target", "ability"],
            "tags": ["death", "ability", "beast"],
        },
        "death.beast.ability.overwhelmed": {
            "kind": "death",
            "text": "{target} не выдерживает натиска {ability} и падает.",
            "variables": ["target", "ability"],
            "tags": ["death", "ability", "beast"],
        },
        # --- cause: execute ---
        "death.beast.execute.put_down": {
            "kind": "death",
            "text": "{source} добивает {target}.",
            "variables": ["source", "target"],
            "tags": ["death", "execute", "beast", "sourced"],
        },
        # --- cause: unknown (no source — R-1) ---
        "death.beast.unknown.falls_silent": {
            "kind": "death",
            "text": "{target} замирает навсегда.",
            "variables": ["target"],
            "tags": ["death", "unknown", "beast"],
        },
        "death.beast.unknown.collapses": {
            "kind": "death",
            "text": "{target} обрушивается на землю.",
            "variables": ["target"],
            "tags": ["death", "unknown", "beast"],
        },
    },
}

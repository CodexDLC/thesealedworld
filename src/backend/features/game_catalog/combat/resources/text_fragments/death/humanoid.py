DEATH_HUMANOID_PHRASES = {
    "death": {
        # --- cause: damage, source known ---
        "death.humanoid.damage.struck_down": {
            "kind": "death",
            "text": "{source} сражает {target} насмерть.",
            "variables": ["source", "target"],
            "tags": ["death", "damage", "humanoid", "sourced"],
        },
        "death.humanoid.damage.knees": {
            "kind": "death",
            "text": "{target} опускается на колени и не встаёт.",
            "variables": ["target"],
            "tags": ["death", "damage", "humanoid"],
        },
        "death.humanoid.damage.cut_down": {
            "kind": "death",
            "text": "{source} разит {target} последним ударом.",
            "variables": ["source", "target"],
            "tags": ["death", "damage", "humanoid", "sourced"],
        },
        # --- cause: dot, effect required (R-2) ---
        "death.humanoid.dot.consumed_by": {
            "kind": "death",
            "text": "{target} сгорает под действием {effect}.",
            "variables": ["target", "effect"],
            "tags": ["death", "dot", "humanoid", "effect_named"],
        },
        "death.humanoid.dot.bleeds_out": {
            "kind": "death",
            "text": "{target} истекает кровью — {effect} сделал своё дело.",
            "variables": ["target", "effect"],
            "tags": ["death", "dot", "humanoid", "effect_named", "bleed"],
        },
        "death.humanoid.dot.corroded": {
            "kind": "death",
            "text": "{effect} окончательно разрушает {target}.",
            "variables": ["target", "effect"],
            "tags": ["death", "dot", "humanoid", "effect_named"],
        },
        # --- cause: ability, ability preferred (R-3) ---
        "death.humanoid.ability.finished_by": {
            "kind": "death",
            "text": "{target} уничтожен {ability} от {source}.",
            "variables": ["target", "ability", "source"],
            "tags": ["death", "ability", "humanoid", "sourced"],
        },
        "death.humanoid.ability.overcome": {
            "kind": "death",
            "text": "{target} не выдерживает {ability}.",
            "variables": ["target", "ability"],
            "tags": ["death", "ability", "humanoid"],
        },
        # --- cause: execute ---
        "death.humanoid.execute.judgement": {
            "kind": "death",
            "text": "{source} выносит приговор: {target} повержен.",
            "variables": ["source", "target"],
            "tags": ["death", "execute", "humanoid", "sourced"],
        },
        "death.humanoid.execute.final_blow": {
            "kind": "death",
            "text": "{target} сломлен последним ударом.",
            "variables": ["target"],
            "tags": ["death", "execute", "humanoid"],
        },
    },
}

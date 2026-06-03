HUMANOID_REACTION_PHRASES = {
    "reaction": {
        # miss — 4
        "body.humanoid.reaction.miss.void": {
            "kind": "reaction",
            "text": "{target} позволяет удару уйти в пустоту",
            "variables": ["target"],
            "tags": ["miss"],
        },
        "body.humanoid.reaction.miss.lean": {
            "kind": "reaction",
            "text": "{target} отклоняется назад",
            "variables": ["target"],
            "tags": ["miss"],
        },
        "body.humanoid.reaction.miss.gap": {
            "kind": "reaction",
            "text": "удар проходит мимо {target}",
            "variables": ["target"],
            "tags": ["miss"],
        },
        "body.humanoid.reaction.miss.natural": {
            "kind": "reaction",
            "text": "атака проходит мимо {target}",
            "variables": ["target"],
            "tags": ["miss"],
        },
        "body.humanoid.reaction.miss.wide": {
            "kind": "reaction",
            "text": "атака уходит в сторону от {target}",
            "variables": ["target"],
            "tags": ["miss"],
        },
        # dodge — 4
        "body.humanoid.reaction.dodge.sidestep": {
            "kind": "reaction",
            "text": "{target} отшагивает с линии атаки",
            "variables": ["target"],
            "tags": ["dodge"],
        },
        "body.humanoid.reaction.dodge.drop": {
            "kind": "reaction",
            "text": "{target} падает ниже удара",
            "variables": ["target"],
            "tags": ["dodge"],
        },
        "body.humanoid.reaction.dodge.roll": {
            "kind": "reaction",
            "text": "{target} уходит перекатом",
            "variables": ["target"],
            "tags": ["dodge"],
        },
        "body.humanoid.reaction.dodge.back": {
            "kind": "reaction",
            "text": "{target} отступает на шаг назад",
            "variables": ["target"],
            "tags": ["dodge"],
        },
        # parry — 4
        "body.humanoid.reaction.parry.deflect": {
            "kind": "reaction",
            "text": "{target} сбивает атаку в сторону",
            "variables": ["target"],
            "tags": ["parry"],
        },
        "body.humanoid.reaction.parry.bind": {
            "kind": "reaction",
            "text": "{target} связывает оружие противника",
            "variables": ["target"],
            "tags": ["parry"],
        },
        "body.humanoid.reaction.parry.sweep": {
            "kind": "reaction",
            "text": "{target} отметает удар клинком",
            "variables": ["target"],
            "tags": ["parry"],
        },
        "body.humanoid.reaction.parry.counter_edge": {
            "kind": "reaction",
            "text": "{target} отбивает лезвие ребром",
            "variables": ["target"],
            "tags": ["parry"],
        },
        # block — 4
        "body.humanoid.reaction.block.shield_take": {
            "kind": "reaction",
            "text": "{target} принимает удар на щит",
            "variables": ["target"],
            "tags": ["block"],
        },
        "body.humanoid.reaction.block.arm": {
            "kind": "reaction",
            "text": "{target} перекрывает удар предплечьем",
            "variables": ["target"],
            "tags": ["block"],
        },
        "body.humanoid.reaction.block.weapon_flat": {
            "kind": "reaction",
            "text": "{target} гасит удар плоскостью оружия",
            "variables": ["target"],
            "tags": ["block"],
        },
        "body.humanoid.reaction.block.brace": {
            "kind": "reaction",
            "text": "{target} упирается и держит удар",
            "variables": ["target"],
            "tags": ["block"],
        },
    },
}

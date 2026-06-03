BEAST_REACTION_PHRASES = {
    "reaction": {
        # miss — 4
        "body.beast.reaction.miss.pass": {
            "kind": "reaction",
            "text": "удар проходит мимо {target}",
            "variables": ["target"],
            "tags": ["miss"],
        },
        "body.beast.reaction.miss.natural": {
            "kind": "reaction",
            "text": "атака проходит мимо {target}",
            "variables": ["target"],
            "tags": ["miss"],
        },
        "body.beast.reaction.miss.low": {
            "kind": "reaction",
            "text": "{target} прижимается к земле",
            "variables": ["target"],
            "tags": ["miss"],
        },
        "body.beast.reaction.miss.gap": {
            "kind": "reaction",
            "text": "удар уходит в пустоту за {target}",
            "variables": ["target"],
            "tags": ["miss"],
        },
        "body.beast.reaction.miss.wide": {
            "kind": "reaction",
            "text": "атака уходит мимо {target}",
            "variables": ["target"],
            "tags": ["miss"],
        },
        # dodge — 4
        "body.beast.reaction.dodge.side_leap": {
            "kind": "reaction",
            "text": "{target} отпрыгивает в сторону",
            "variables": ["target"],
            "tags": ["dodge"],
        },
        "body.beast.reaction.dodge.back": {
            "kind": "reaction",
            "text": "{target} откатывается назад",
            "variables": ["target"],
            "tags": ["dodge"],
        },
        "body.beast.reaction.dodge.low": {
            "kind": "reaction",
            "text": "{target} ныряет под удар",
            "variables": ["target"],
            "tags": ["dodge"],
        },
        "body.beast.reaction.dodge.roll": {
            "kind": "reaction",
            "text": "{target} уходит перекатом на бок",
            "variables": ["target"],
            "tags": ["dodge"],
        },
        # parry — 4
        "body.beast.reaction.parry.paw_swipe": {
            "kind": "reaction",
            "text": "{target} сбивает атаку лапой",
            "variables": ["target"],
            "tags": ["parry"],
        },
        "body.beast.reaction.parry.head_push": {
            "kind": "reaction",
            "text": "{target} отталкивает атаку мордой",
            "variables": ["target"],
            "tags": ["parry"],
        },
        "body.beast.reaction.parry.body_turn": {
            "kind": "reaction",
            "text": "{target} разворачивается и уводит удар вскользь",
            "variables": ["target"],
            "tags": ["parry"],
        },
        "body.beast.reaction.parry.tail_sweep": {
            "kind": "reaction",
            "text": "{target} отбивает атаку хвостом",
            "variables": ["target"],
            "tags": ["parry"],
        },
        # block — 4
        "body.beast.reaction.block.hide": {
            "kind": "reaction",
            "text": "{target} подставляет загривок",
            "variables": ["target"],
            "tags": ["block"],
        },
        "body.beast.reaction.block.shoulder": {
            "kind": "reaction",
            "text": "{target} принимает удар на плечо",
            "variables": ["target"],
            "tags": ["block"],
        },
        "body.beast.reaction.block.skull": {
            "kind": "reaction",
            "text": "{target} подставляет лоб",
            "variables": ["target"],
            "tags": ["block"],
        },
        "body.beast.reaction.block.paw_guard": {
            "kind": "reaction",
            "text": "{target} загораживается лапой",
            "variables": ["target"],
            "tags": ["block"],
        },
    },
}

ITEM_THROWN_PHRASES = {
    "item_use": {
        "item.thrown.default.use.throw": {
            "kind": "item_use",
            "text": "{source} бросает {item} в сторону {target}",
            "variables": ["source", "item", "target"],
            "tags": ["item", "thrown"],
        },
    },
    "item_target_result": {
        "item.thrown.default.target.hit": {
            "kind": "item_target_result",
            "text": "{target} получает {damage} урона",
            "variables": ["target", "damage"],
            "tags": ["item", "thrown", "hit"],
        },
        "item.thrown.default.target.miss": {
            "kind": "item_target_result",
            "text": "{target} уходит с линии броска",
            "variables": ["target"],
            "tags": ["item", "thrown", "miss"],
        },
    },
    "item_resource": {},
}

THROWN_ITEM_TEMPLATE_EXAMPLES = ()

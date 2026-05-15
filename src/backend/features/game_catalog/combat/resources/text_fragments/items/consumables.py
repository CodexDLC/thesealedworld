ITEM_CONSUMABLE_PHRASES = {
    "item_use": {
        "item.consumable.minor_healing_potion.use.drink": {
            "kind": "item_use",
            "text": "{source} выпивает {item}",
            "variables": ["source", "item"],
            "tags": ["item", "consumable", "heal"],
        },
    },
    "item_target_result": {
        "item.consumable.minor_healing_potion.target.heal": {
            "kind": "item_target_result",
            "text": "{target} восстанавливает {healing} здоровья",
            "variables": ["target", "healing"],
            "tags": ["item", "consumable", "heal"],
        },
    },
    "item_resource": {
        "item.consumable.minor_healing_potion.resource.no_resource": {
            "kind": "item_resource",
            "text": "{source} не может использовать {item}",
            "variables": ["source", "item"],
            "tags": ["item", "consumable", "no_resource"],
        },
    },
}

CONSUMABLE_ITEM_TEMPLATE_EXAMPLES = (
    {
        "template_key": "combat.item.minor_healing_potion.use.single",
        "resource_type": "item",
        "resource_id": "minor_healing_potion",
        "catalog_key": "combat.item.minor_healing_potion",
        "outcome": "heal",
        "delivery": "single",
        "pattern": "{use}: {target_results}.",
        "phrase_keys": {"use": "item.consumable.minor_healing_potion.use.drink"},
        "slots": {"target_results": "list"},
        "joiners": {"target_results": ", "},
        "tags": ["item", "consumable", "heal", "single"],
    },
    {
        "template_key": "combat.item.minor_healing_potion.target.heal.humanoid",
        "resource_type": "item",
        "resource_id": "minor_healing_potion",
        "catalog_key": "combat.item.minor_healing_potion",
        "outcome": "heal",
        "target_body": "humanoid",
        "pattern": "{target_result}",
        "phrase_keys": {"target_result": "item.consumable.minor_healing_potion.target.heal"},
        "tags": ["item", "consumable", "target", "heal", "humanoid"],
    },
)

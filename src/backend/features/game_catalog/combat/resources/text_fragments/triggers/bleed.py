TRIGGER_BLEED_PHRASES = {
    "trigger_proc": {
        "trigger.bleed.serrated.open": {
            "kind": "trigger_proc",
            "text": "{trigger} открывает кровотечение у {target}",
            "variables": ["trigger", "target"],
            "tags": ["trigger", "bleed"],
        },
    },
    "trigger_proc_result": {},
    "trigger_effect_result": {
        "trigger.bleed.serrated.effect.apply": {
            "kind": "trigger_effect_result",
            "text": "{effect} закрепляется на {target}",
            "variables": ["effect", "target"],
            "tags": ["trigger", "bleed", "effect"],
        },
    },
    "trigger_damage_result": {
        "trigger.bleed.serrated.damage.bonus": {
            "kind": "trigger_damage_result",
            "text": "{trigger} добавляет {damage} урона кровотечением",
            "variables": ["trigger", "damage"],
            "tags": ["trigger", "bleed", "damage"],
        },
    },
}

BLEED_TRIGGER_TEMPLATE_EXAMPLES = (
    {
        "template_key": "combat.trigger.weapon_serrated_bleed_crit.proc.hit",
        "resource_type": "trigger",
        "resource_id": "weapon_serrated_bleed_crit",
        "catalog_key": "combat.trigger.weapon.serrated_bleed_crit",
        "outcome": "hit_proc",
        "pattern": "{proc_result}.",
        "phrase_keys": {"proc_result": "trigger.bleed.serrated.open"},
        "tags": ["trigger", "bleed", "hit"],
    },
    {
        "template_key": "combat.trigger.weapon_serrated_bleed_crit.effect.apply",
        "resource_type": "trigger",
        "resource_id": "weapon_serrated_bleed_crit",
        "catalog_key": "combat.trigger.weapon.serrated_bleed_crit",
        "outcome": "apply",
        "pattern": "{effect_result}.",
        "phrase_keys": {"effect_result": "trigger.bleed.serrated.effect.apply"},
        "tags": ["trigger", "bleed", "effect"],
    },
    {
        "template_key": "combat.trigger.weapon_serrated_bleed_crit.damage.bonus",
        "resource_type": "trigger",
        "resource_id": "weapon_serrated_bleed_crit",
        "catalog_key": "combat.trigger.weapon.serrated_bleed_crit",
        "outcome": "damage_bonus",
        "pattern": "{damage_result}.",
        "phrase_keys": {"damage_result": "trigger.bleed.serrated.damage.bonus"},
        "tags": ["trigger", "bleed", "damage"],
    },
)

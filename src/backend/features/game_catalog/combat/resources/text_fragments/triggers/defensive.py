TRIGGER_DEFENSIVE_PHRASES = {
    "trigger_proc": {
        "trigger.defensive.shield_bash.block.open": {
            "kind": "trigger_proc",
            "text": "{trigger} срабатывает после блока {target}",
            "variables": ["trigger", "target"],
            "tags": ["trigger", "defensive", "block"],
        },
    },
    "trigger_proc_result": {
        "trigger.defensive.shield_bash.result.extra_strike": {
            "kind": "trigger_proc_result",
            "text": "{target} получает возможность ответить щитом",
            "variables": ["target"],
            "tags": ["trigger", "defensive", "extra_strike"],
        },
    },
    "trigger_effect_result": {},
    "trigger_damage_result": {},
}

DEFENSIVE_TRIGGER_TEMPLATE_EXAMPLES = (
    {
        "template_key": "combat.trigger.weapon_shield_bash_on_block.proc.block",
        "resource_type": "trigger",
        "resource_id": "weapon_shield_bash_on_block",
        "catalog_key": "combat.trigger.weapon.shield_bash_on_block",
        "outcome": "block_proc",
        "pattern": "{proc}: {proc_results}.",
        "phrase_keys": {"proc": "trigger.defensive.shield_bash.block.open"},
        "slots": {"proc_results": "list"},
        "joiners": {"proc_results": ", "},
        "tags": ["trigger", "defensive", "block"],
    },
)

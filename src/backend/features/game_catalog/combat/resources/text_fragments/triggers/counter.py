TRIGGER_COUNTER_PHRASES = {
    "trigger_proc": {
        "trigger.counter.riposte.parry.open": {
            "kind": "trigger_proc",
            "text": "{target} ловит момент для {trigger}",
            "variables": ["target", "trigger"],
            "tags": ["trigger", "counter", "parry"],
        },
        "trigger.counter.dodge.open": {
            "kind": "trigger_proc",
            "text": "{target} уходит с линии атаки и запускает {trigger}",
            "variables": ["target", "trigger"],
            "tags": ["trigger", "counter", "dodge"],
        },
    },
    "trigger_proc_result": {
        "trigger.counter.riposte.result.counter": {
            "kind": "trigger_proc_result",
            "text": "{target} открывает контратаку по {source}",
            "variables": ["target", "source"],
            "tags": ["trigger", "counter"],
        },
    },
    "trigger_effect_result": {},
    "trigger_damage_result": {},
}

COUNTER_TRIGGER_TEMPLATE_EXAMPLES = (
    {
        "template_key": "combat.trigger.weapon_riposte_on_parry.proc.parry",
        "resource_type": "trigger",
        "resource_id": "weapon_riposte_on_parry",
        "catalog_key": "combat.trigger.weapon.riposte_on_parry",
        "outcome": "parry_proc",
        "pattern": "{proc}: {proc_results}.",
        "phrase_keys": {"proc": "trigger.counter.riposte.parry.open"},
        "slots": {"proc_results": "list"},
        "joiners": {"proc_results": ", "},
        "tags": ["trigger", "counter", "parry"],
    },
    {
        "template_key": "combat.trigger.counter_on_dodge.proc.dodge",
        "resource_type": "trigger",
        "resource_id": "counter_on_dodge",
        "catalog_key": "combat.trigger.dodge.counter_on_dodge",
        "outcome": "dodge_proc",
        "pattern": "{proc}: {proc_results}.",
        "phrase_keys": {"proc": "trigger.counter.dodge.open"},
        "slots": {"proc_results": "list"},
        "joiners": {"proc_results": ", "},
        "tags": ["trigger", "counter", "dodge"],
    },
)

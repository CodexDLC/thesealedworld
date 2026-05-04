from src.backend.resources.game_data.triggers.schemas import TriggerDTO

ON_CRIT_RULES = [
    # --- EFFECTS (Эффекты) ---
    TriggerDTO(
        id="bleed_on_crit",
        name_ru="Кровотечение (Крит)",
        description_ru="Критические удары вызывают глубокое кровотечение.",
        event="ON_CRIT",
        chance=1.0,
        mutations={
            "formula.crit_damage_boost": False,
            "add_effect": {"id": "bleed"},
        },
    ),
    TriggerDTO(
        id="stun_on_crit",
        name_ru="Оглушение (Крит)",
        description_ru="Критические удары оглушают противника.",
        event="ON_CRIT",
        chance=1.0,
        mutations={
            "formula.crit_damage_boost": True,  # С уроном
            "add_effect": {"id": "stun"},
        },
    ),
    # --- DAMAGE MODIFIERS (Урон) ---
    TriggerDTO(
        id="heavy_strike_on_crit",
        name_ru="Сокрушительный Крит",
        description_ru="Критические удары наносят тройной урон.",
        event="ON_CRIT",
        chance=1.0,
        mutations={
            "formula.crit_damage_boost": True,
            "mods.weapon_effect_value": 3.0,  # x3
        },
    ),
    # --- TACTICAL (Механика) ---
    TriggerDTO(
        id="true_crit",
        name_ru="Верный Крит",
        description_ru="От критического удара невозможно уклониться.",
        event="ON_CRIT",
        chance=1.0,
        mutations={
            "force.hit_evasion": True,
        },
    ),
    TriggerDTO(
        id="unblockable_crit",
        name_ru="Пробивающий Крит",
        description_ru="Критический удар игнорирует блок щитом.",
        event="ON_CRIT",
        chance=1.0,
        mutations={
            "restriction.ignore_block": True,
        },
    ),
    TriggerDTO(
        id="piercing_crit",
        name_ru="Пронзающий Крит",
        description_ru="Критический удар игнорирует броню.",
        event="ON_CRIT",
        chance=1.0,
        mutations={
            "formula.can_pierce": True,
        },
    ),
]

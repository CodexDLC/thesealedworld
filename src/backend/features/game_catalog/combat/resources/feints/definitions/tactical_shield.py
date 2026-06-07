from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatDescriptionDTO,
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

_TACTICAL_SHIELD_TAGS = ["tactical", "shield", "skill_shield_mastery", "block", "preparation", "defense"]


TACTICAL_SHIELD_FEINTS_TECHNICAL = {
    "active_defense": FeintTechnicalDTO(
        feint_id="active_defense",
        cost=FeintCostDTO(tactics={"block": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "damage_reduction"],
        purchase_group="tactical",
        preparation_effects=[
            {"id": "prep_active_defense", "target_actor": "source"},
        ],
    ),
    "full_defense": FeintTechnicalDTO(
        feint_id="full_defense",
        cost=FeintCostDTO(tactics={"block": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "damage_cap"],
        purchase_group="tactical",
        preparation_effects=[
            {"id": "prep_full_defense", "target_actor": "source"},
        ],
    ),
    "absolute_defense": FeintTechnicalDTO(
        feint_id="absolute_defense",
        cost=FeintCostDTO(tactics={"block": 7}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "damage_cap", "absolute_defense"],
        purchase_group="tactical",
        preparation_effects=[
            {"id": "prep_absolute_defense", "target_actor": "source"},
        ],
    ),
    "aggressive_defense": FeintTechnicalDTO(
        feint_id="aggressive_defense",
        cost=FeintCostDTO(tactics={"hit": 2, "block": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "damage_cap", "reflect"],
        purchase_group="tactical",
        preparation_effects=[
            {"id": "prep_aggressive_defense", "target_actor": "source"},
        ],
    ),
    "read_tactic": FeintTechnicalDTO(
        feint_id="read_tactic",
        cost=FeintCostDTO(tactics={"hit": 1, "block": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "dispel", "preparation_purge"],
        purchase_group="tactical",
        effects=[
            {"id": "dispel_preparations", "target_actor": "target"},
        ],
    ),
    "scarlet_riposte": FeintTechnicalDTO(
        feint_id="scarlet_riposte",
        cost=FeintCostDTO(tactics={"blood": 1, "block": 2, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "blood", "parry", "preparation", "reflect", "counter"],
        purchase_group="tactical",
        preparation_effects=[
            {
                "id": "prep_scarlet_riposte",
                "target_actor": "source",
                "params": {"reflect_damage": 10},
            },
        ],
    ),
    "shield_anti_dispel_brace": FeintTechnicalDTO(
        feint_id="shield_anti_dispel_brace",
        cost=FeintCostDTO(tactics={"block": 4}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "anti_dispel", "preparation_guard"],
        purchase_group="tactical",
        preparation_effects=[
            {"id": "prep_shield_anti_dispel_brace", "target_actor": "source"},
        ],
    ),
    "shield_focused_pressure": FeintTechnicalDTO(
        feint_id="shield_focused_pressure",
        cost=FeintCostDTO(tactics={"block": 2, "parry": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.0,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "debuff_accuracy", "multi_target", "team_tempo"],
        purchase_group="tactical",
        effects=[
            {"id": "debuff_accuracy", "target_actor": "target"},
        ],
    ),
    "shield_blood_ward": FeintTechnicalDTO(
        feint_id="shield_blood_ward",
        cost=FeintCostDTO(tactics={"blood": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "blood", "preparation", "damage_reduction"],
        purchase_group="tactical",
        preparation_effects=[
            {"id": "prep_shield_blood_ward", "target_actor": "source", "params": {"reduction": 0.30}},
        ],
    ),
    "read_tactic_advanced": FeintTechnicalDTO(
        feint_id="read_tactic_advanced",
        cost=FeintCostDTO(tactics={"hit": 1, "block": 2, "tempo": 1}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "tempo", "dispel", "preparation_purge", "punish"],
        purchase_group="tactical",
        effects=[
            {"id": "dispel_preparations", "target_actor": "target"},
            {"id": "debuff_accuracy", "target_actor": "target"},
        ],
    ),
    "shield_blood_mend": FeintTechnicalDTO(
        feint_id="shield_blood_mend",
        cost=FeintCostDTO(tactics={"blood": 3, "block": 1}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "blood", "heal"],
        purchase_group="tactical",
        effects=[
            {"id": "shield_blood_heal", "target_actor": "source", "params": {"heal_max_hp_ratio": 0.15}},
        ],
    ),
}

_TACTICAL_SHIELD_TEXTS = {
    "active_defense": (
        "Активная защита",
        "закрывая линию щитом принять следующий удар",
        "Тактический щитовой финт: следующий входящий удар принудительно уходит в защитную ветку щита.",
        "закрывая линию щитом",
        "и оставляет щит на линии активной защиты",
        "и жестко собирает активную защиту",
    ),
    "full_defense": (
        "Полная защита",
        "уходя за полную защиту свести следующий удар к минимуму",
        "Тактический щитовой финт: следующий входящий удар уходит в усиленную защитную ветку щита.",
        "уходя за полную защиту щита",
        "и удерживает щит в полной защите",
        "и закрывает корпус полной защитой",
    ),
    "absolute_defense": (
        "Абсолютная защита",
        "собирая абсолютную защиту закрыться до следующего размена",
        "Тактический щитовой финт: до следующего размена входящий урон через resolver становится не больше 1.",
        "собирая абсолютную защиту",
        "и удерживает абсолютную защиту",
        "и превращает щит в неподвижную стену",
    ),
    "aggressive_defense": (
        "Агрессивная защита",
        "давя щитом вперед встретить следующий удар",
        "Тактический щитовой финт: следующий входящий удар уходит в контр-ветку щита.",
        "закрываясь щитом с давлением вперед",
        "и удерживает щит для жесткой встречи",
        "и готовит щит к болезненному ответу",
    ),
    "read_tactic": (
        "Разгадать тактику",
        "выискивая подготовку противника сорвать её",
        "Тактический щитовой финт: при попадании снимает подготовленные приемы с цели.",
        "выискивая подготовку противника",
        "и сбивает подготовленную линию защиты",
        "и разрушает тактическую заготовку цели",
    ),
    "scarlet_riposte": (
        "Алый рипост",
        "оставляя кровь на линии подготовить кровавый ответ",
        "Тактический щитовой финт: следующий блок или парирование возвращает урон атакующему.",
        "оставляя кровь на линии ответа",
        "и держит щит для алого рипоста",
        "и превращает защиту в болезненный ответ",
    ),
    "shield_anti_dispel_brace": (
        "Опора подготовки",
        "удерживая щит сохранить подготовку",
        "Тактический щитовой финт: следующее снятие подготовок противником снимет только одну, а не все.",
        "удерживая щит как опору подготовки",
        "и удерживает линию подготовки несмотря на давление",
        "и крепко закрепляет подготовку щитом",
    ),
    "shield_focused_pressure": (
        "Давление на строй",
        "давя щитом сбить точность строю",
        "Тактический щитовой финт: щитовым давлением сбивает точность сразу нескольким врагам.",
        "вынося щит на ширину линии",
        "и сбивает точность всему строю",
        "и навязывает давление на весь фронт",
    ),
    "shield_blood_ward": (
        "Кровавая защита",
        "впитав боль уплотнить защиту",
        "Тактический щитовой финт: тратит кровь и снижает следующий входящий удар на 30%.",
        "впитывая пережитую боль в защиту",
        "и переводит боль в уплотненную защиту",
        "и закрывает следующий удар кровавой защитой",
    ),
    "read_tactic_advanced": (
        "Карательная разгадка",
        "наказывая подготовку противника сорвать её и сбить ему точность",
        "Карательный щитовой финт: тратит темп, снимает подготовленные приемы с цели и сбивает ей точность.",
        "наказывая подготовку противника",
        "и срывает подготовку и сбивает точность цели",
        "и срывает подготовку цели сокрушительной разгадкой",
    ),
    "shield_blood_mend": (
        "Кровавое восстановление",
        "обратив боль в выдох восстановиться",
        "Тактический щитовой финт: тратит кровь и восстанавливает 15% максимального HP.",
        "обращая пережитую боль в выдох",
        "и восстанавливается через кровавую перевязку",
        "и крепко восстанавливает дыхание",
    ),
}


def _tactical_shield_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _TACTICAL_SHIELD_TEXTS[feint_id]
    return build_combat_description(
        resource_type="feints",
        resource_id=feint_id,
        icon=f"combat/feints/{feint_id}.svg",
        display_name=display_name,
        ui_label=ui_label,
        short_description=short,
        humanoid_long_description=short,
        humanoid_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но сохраняет щитовую подготовку"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} отводит атаку"],
            block=["но {target} принимает удар на защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но сохраняет щитовую подготовку"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} сбивает атаку движением"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


TACTICAL_SHIELD_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_tactical_shield_description(feint_id),
    )
    for feint_id, technical in TACTICAL_SHIELD_FEINTS_TECHNICAL.items()
}

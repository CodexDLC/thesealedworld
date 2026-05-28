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
    "concussion": FeintTechnicalDTO(
        feint_id="concussion",
        cost=FeintCostDTO(tactics={"block": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TACTICAL_SHIELD_TAGS, "shield_bash", "control"],
        purchase_group="tactical",
        shield_guard_damage_ratio=0.25,
        shield_guard_damage_min=3,
        shield_guard_damage_tier_fallback=3,
        effects=[
            {"id": "concussed_no_feints", "target_actor": "target"},
        ],
    ),
}

_TACTICAL_SHIELD_TEXTS = {
    "active_defense": (
        "Активная защита",
        "Принять следующий удар щитом",
        "Тактический щитовой финт: следующий входящий урон через resolver уменьшается вдвое.",
        "закрывая линию щитом",
        "и оставляет щит на линии активной защиты",
        "и жестко собирает активную защиту",
    ),
    "full_defense": (
        "Полная защита",
        "Свести следующий удар к минимуму",
        "Тактический щитовой финт: следующий входящий урон через resolver становится не больше 1.",
        "уходя за полную защиту щита",
        "и удерживает щит в полной защите",
        "и закрывает корпус полной защитой",
    ),
    "absolute_defense": (
        "Абсолютная защита",
        "Закрыться до следующего размена",
        "Тактический щитовой финт: до следующего размена входящий урон через resolver становится не больше 1.",
        "собирая абсолютную защиту",
        "и удерживает абсолютную защиту",
        "и превращает щит в неподвижную стену",
    ),
    "aggressive_defense": (
        "Агрессивная защита",
        "Встретить удар щитом",
        "Тактический щитовой финт: следующий входящий урон становится не больше 1 и отражает урон щитом.",
        "закрываясь щитом с давлением вперед",
        "и удерживает щит для жесткой встречи",
        "и готовит щит к болезненному ответу",
    ),
    "read_tactic": (
        "Разгадать тактику",
        "Сорвать подготовку противника",
        "Тактический щитовой финт: при попадании снимает подготовленные приемы с цели.",
        "выискивая подготовку противника",
        "и сбивает подготовленную линию защиты",
        "и разрушает тактическую заготовку цели",
    ),
    "concussion": (
        "Контузия",
        "Оглушить ударом щита",
        "Тактический щитовой финт: удар щитом наносит урон и запрещает цели финты на следующий размен.",
        "вынося щит в короткий удар",
        "и попадает щитом в корпус",
        "и жестко срывает концентрацию цели",
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

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

_BASIC_DODGE_TAGS = ["basic", "dodge", "preparation", "defense"]


BASIC_DODGE_FEINTS_TECHNICAL = {
    "glancing_step": FeintTechnicalDTO(
        feint_id="glancing_step",
        cost=FeintCostDTO(tactics={"dodge": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_BASIC_DODGE_TAGS, "damage_reduction"],
        preparation_effects=[
            {"id": "prep_glancing_dodge", "target_actor": "source"},
        ],
    ),
    "wind_dance": FeintTechnicalDTO(
        feint_id="wind_dance",
        cost=FeintCostDTO(tactics={"dodge": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_BASIC_DODGE_TAGS, "counter_cap"],
        preparation_effects=[
            {"id": "prep_counter_cap_on_dodge", "target_actor": "source"},
        ],
    ),
    "blade_dance": FeintTechnicalDTO(
        feint_id="blade_dance",
        cost=FeintCostDTO(tactics={"dodge": 7}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_BASIC_DODGE_TAGS, "counter"],
        preparation_effects=[
            {"id": "prep_counter_on_dodge", "target_actor": "source"},
        ],
    ),
}

_BASIC_DODGE_TEXTS = {
    "glancing_step": (
        "Скользящий отход",
        "Принять удар вскользь",
        "Базовый dodge-финт: следующий входящий удар наносит половину урона.",
        "оставляя корпус в скользящей позиции",
        "и сохраняет смещение после попадания",
        "и закрепляет опасное смещение корпуса",
    ),
    "wind_dance": (
        "Танец ветра",
        "Оставить окно для ответа",
        "Базовый dodge-финт: следующий успешный уворот проверяет контратаку по капу.",
        "сохраняя движение для ответного окна",
        "и не теряет ритм для отхода",
        "и закрепляет выгодный ритм движения",
    ),
    "blade_dance": (
        "Танец лезвий",
        "Уйти с линии и ударить в ответ",
        "Базовый dodge-финт: следующий успешный уворот вызывает контратаку.",
        "оставляя путь для ответного удара",
        "и сохраняет дистанцию после попадания",
        "и сохраняет линию для опасного ответа",
    ),
}


def _basic_dodge_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _BASIC_DODGE_TEXTS[feint_id]
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
            miss=["но сохраняет подготовленное движение"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} сбивает атаку"],
            block=["но {target} принимает удар на защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но сохраняет подготовленное движение"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} сбивает атаку движением"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


BASIC_DODGE_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_basic_dodge_description(feint_id),
    )
    for feint_id, technical in BASIC_DODGE_FEINTS_TECHNICAL.items()
}

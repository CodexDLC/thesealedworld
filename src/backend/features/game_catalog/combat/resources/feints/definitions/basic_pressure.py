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

_BASIC_PRESSURE_TAGS = ["basic", "pressure", "preparation", "defense", "damage_reduction"]


BASIC_PRESSURE_FEINTS_TECHNICAL = {
    "press_defense": FeintTechnicalDTO(
        feint_id="press_defense",
        cost=FeintCostDTO(tactics={"pressure": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_BASIC_PRESSURE_TAGS],
        preparation_effects=[
            {"id": "prep_brace_guard", "target_actor": "source"},
        ],
    ),
}

_BASIC_PRESSURE_TEXTS = {
    "press_defense": (
        "Защитный нажим",
        "Закрепиться после удара",
        "Базовый pressure-финт: следующий входящий удар наносит меньше урона.",
        "закрепляя линию после нанесенного урона",
        "и переводит нажим в защитную стойку",
        "и жестко закрывает корпус после давления",
    ),
}


def _basic_pressure_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _BASIC_PRESSURE_TEXTS[feint_id]
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
            miss=["но не успевает закрепить защитную линию"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} сбивает атаку"],
            block=["но {target} принимает удар на защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но не успевает закрепить защитную линию"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} сбивает атаку движением"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


BASIC_PRESSURE_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_basic_pressure_description(feint_id),
    )
    for feint_id, technical in BASIC_PRESSURE_FEINTS_TECHNICAL.items()
}

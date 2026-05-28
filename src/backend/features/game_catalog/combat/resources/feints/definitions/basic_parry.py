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

_BASIC_PARRY_TAGS = ["basic", "parry", "preparation", "defense"]


BASIC_PARRY_FEINTS_TECHNICAL = {
    "foresight_parry": FeintTechnicalDTO(
        feint_id="foresight_parry",
        cost=FeintCostDTO(tactics={"parry": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_BASIC_PARRY_TAGS, "forced_parry"],
        preparation_effects=[
            {"id": "prep_foresight_parry", "target_actor": "source"},
        ],
    ),
    "second_breath": FeintTechnicalDTO(
        feint_id="second_breath",
        cost=FeintCostDTO(tactics={"parry": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_BASIC_PARRY_TAGS, "heal"],
        preparation_effects=[
            {
                "id": "prep_second_breath",
                "target_actor": "source",
                "params": {"heal_max_hp_ratio": 0.18, "heal_min": 8},
            },
        ],
    ),
    "perfect_riposte": FeintTechnicalDTO(
        feint_id="perfect_riposte",
        cost=FeintCostDTO(tactics={"parry": 7}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_BASIC_PARRY_TAGS, "heal", "counter"],
        preparation_effects=[
            {
                "id": "prep_perfect_riposte",
                "target_actor": "source",
                "params": {"heal_max_hp_ratio": 0.12, "heal_min": 6},
            },
        ],
    ),
}

_BASIC_PARRY_TEXTS = {
    "foresight_parry": (
        "Предвидение",
        "Подготовить следующее парирование",
        "Базовый parry-финт: следующий входящий удар будет парирован.",
        "оставляя оружие на линии парирования",
        "и сохраняет готовность встретить следующий удар",
        "и жестко закрывает линию ответа",
    ),
    "second_breath": (
        "Второе дыхание",
        "Восстановиться на парировании",
        "Базовый parry-финт: следующее успешное парирование восстанавливает HP.",
        "переводя дыхание в защитную стойку",
        "и удерживает восстановительный ритм",
        "и закрепляет стойку для сильного восстановления",
    ),
    "perfect_riposte": (
        "Совершенный рипост",
        "Парировать, восстановиться и ответить",
        "Базовый parry-финт: следующее успешное парирование восстанавливает HP и вызывает контратаку.",
        "сохраняя оружие для рипоста",
        "и держит линию ответа после контакта",
        "и открывает опасный рипост",
    ),
}


def _basic_parry_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _BASIC_PARRY_TEXTS[feint_id]
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
            miss=["но сохраняет подготовленную защиту"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} отводит атаку"],
            block=["но {target} принимает удар на защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но сохраняет подготовленную защиту"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} сбивает атаку движением"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


BASIC_PARRY_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_basic_parry_description(feint_id),
    )
    for feint_id, technical in BASIC_PARRY_FEINTS_TECHNICAL.items()
}

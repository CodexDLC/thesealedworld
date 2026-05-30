from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatDescriptionDTO,
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import pipeline_mutation
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

_RANGED_TACTICAL_TAGS = ["tactical", "ranged_combat", "skill_ranged_combat", "ranged"]


TACTICAL_RANGED_FEINTS_TECHNICAL = {
    "reveal_intentions": FeintTechnicalDTO(
        feint_id="reveal_intentions",
        cost=FeintCostDTO(tactics={"hit": 2, "dodge": 1}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "hit", "dodge", "dispel", "preparation_purge"],
        purchase_group="tactical",
        effects=[
            {"id": "dispel_preparations", "target_actor": "target"},
        ],
    ),
    "covering_position": FeintTechnicalDTO(
        feint_id="covering_position",
        cost=FeintCostDTO(tactics={"hit": 2, "dodge": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "hit", "dodge", "damage_reduction"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_glancing_dodge", "target_actor": "source"}],
    ),
    "backstep_shot": FeintTechnicalDTO(
        feint_id="backstep_shot",
        cost=FeintCostDTO(tactics={"dodge": 3, "counter": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "dodge", "counter"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_counter_on_dodge", "target_actor": "source"}],
    ),
    "open_distance": FeintTechnicalDTO(
        feint_id="open_distance",
        cost=FeintCostDTO(tactics={"dodge": 5, "counter": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "dodge", "counter_cap"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_counter_cap_on_dodge", "target_actor": "source"}],
    ),
    "blinding_shot": FeintTechnicalDTO(
        feint_id="blinding_shot",
        cost=FeintCostDTO(tactics={"hit": 4, "dodge": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "hit", "dodge", "accuracy_debuff"],
        purchase_group="tactical",
        effects=[
            {"id": "debuff_accuracy", "target_actor": "target"},
        ],
    ),
    "ranged_covering_volley": FeintTechnicalDTO(
        feint_id="ranged_covering_volley",
        cost=FeintCostDTO(tactics={"hit": 4, "dodge": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=5,
        secondary_damage_mult=0.45,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "hit", "dodge", "damage", "multi_target"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.90),
            pipeline_mutation("suppress_crit_triggers"),
        ],
    ),
}

_RANGED_TEXTS = {
    "reveal_intentions": (
        "Раскрыть намерения",
        "Сорвать подготовку цели",
        "Тактический финт дальнего боя: при попадании снимает подготовленные приемы с цели.",
        "читая движение цели по дистанции",
        "и срывает подготовленную линию цели",
        "и выбивает цель из заготовленного приема",
    ),
    "covering_position": (
        "Позиция прикрытия",
        "Снизить следующий входящий урон",
        "Тактический финт дальнего боя: следующий входящий удар наносит половину урона.",
        "занимая позицию под прикрытием",
        "и оставляет путь для скользящего отхода",
        "и принимает давление вскользь",
    ),
    "backstep_shot": (
        "Отстрел на отходе",
        "Уворот в контратаку",
        "Тактический финт дальнего боя: следующий успешный уворот вызывает контратаку.",
        "готовя выстрел на отходе",
        "и держит тетиву для ответного окна",
        "и переводит уход в ответный выстрел",
    ),
    "open_distance": (
        "Разрыв дистанции",
        "Контратака от капа",
        "Тактический финт дальнего боя: следующий успешный уворот проверяет контратаку по капу.",
        "разрывая дистанцию перед выстрелом",
        "и открывает предельное окно ответа",
        "и ловит цель на разрыве дистанции",
    ),
    "blinding_shot": (
        "Ослепляющий выстрел",
        "Сбить точность цели",
        "Тактический финт дальнего боя: при попадании снижает точность цели.",
        "целится в линию зрения",
        "и сбивает прицел цели",
        "и заставляет цель потерять линию атаки",
    ),
    "ranged_covering_volley": (
        "Прикрывающий залп",
        "Накрыть пять целей",
        "Тактический финт дальнего боя: основной размен задевает до четырех дополнительных целей.",
        "раскладывая выстрелы по сектору",
        "и накрывает сектор прикрывающим залпом",
        "и удерживает несколько целей под давлением",
    ),
}


def _ranged_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _RANGED_TEXTS[feint_id]
    return build_combat_description(
        resource_type="feints",
        resource_id=feint_id,
        icon=f"combat/feints/{feint_id}.svg",
        display_name=display_name,
        ui_label=ui_label,
        short_description=short,
        humanoid_long_description=short,
        humanoid_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} держит {{target}} на дистанции, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но дистанция не дает результата"],
            dodge=["но {target} уходит с линии выстрела"],
            parry=["но {target} сбивает траекторию"],
            block=["но {target} закрывает линию выстрела"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} держит {{target}} на дистанции, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но дистанция не дает результата"],
            dodge=["но {target} уходит с линии выстрела"],
            parry=["но {target} сбивает траекторию движением"],
            block=["но выстрел гаснет о защиту {target}"],
        ),
    )


TACTICAL_RANGED_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_ranged_description(feint_id),
    )
    for feint_id, technical in TACTICAL_RANGED_FEINTS_TECHNICAL.items()
}

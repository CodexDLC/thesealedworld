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
        cost=FeintCostDTO(tactics={"hit": 2, "tempo": 1}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "hit", "tempo", "position_control", "read_intent"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("ranged.far_weight_bonus", 0.20),
            pipeline_mutation("ranged.close_weight_bonus", -0.15),
            pipeline_mutation("ranged.enemy_pressure_mult", 0.75),
        ],
    ),
    "covering_position": FeintTechnicalDTO(
        feint_id="covering_position",
        cost=FeintCostDTO(tactics={"dodge": 3, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "dodge", "tempo", "position_control", "stabilize"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("ranged.next_position_min", "mid"),
            pipeline_mutation("ranged.damage_pressure_mult", 0.50),
            pipeline_mutation("ranged.mid_weight_bonus", 0.20),
            pipeline_mutation("ranged.close_weight_bonus", -0.15),
        ],
    ),
    "backstep_shot": FeintTechnicalDTO(
        feint_id="backstep_shot",
        cost=FeintCostDTO(tactics={"hit": 2, "dodge": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "hit", "dodge", "position_shift", "accuracy"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("ranged.current_position_step", 1),
            pipeline_mutation("ranged.far_weight_bonus", 0.15),
            pipeline_mutation("ranged.close_weight_bonus", -0.10),
            pipeline_mutation("ranged.outgoing_accuracy_bonus_mult", 1.05),
        ],
    ),
    "open_distance": FeintTechnicalDTO(
        feint_id="open_distance",
        cost=FeintCostDTO(tactics={"dodge": 5, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "dodge", "tempo", "position_shift", "far"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("ranged.current_position_min", "mid"),
            pipeline_mutation("ranged.next_position_override", "far"),
            pipeline_mutation("ranged.damage_pressure_mult", 0.70),
        ],
    ),
    "blinding_shot": FeintTechnicalDTO(
        feint_id="blinding_shot",
        cost=FeintCostDTO(tactics={"hit": 3, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "hit", "tempo", "position_control", "pressure"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("ranged.enemy_pressure_mult", 0.60),
            pipeline_mutation("ranged.far_weight_bonus", 0.20),
            pipeline_mutation("ranged.close_weight_bonus", -0.20),
        ],
    ),
    "ranged_terrain_read": FeintTechnicalDTO(
        feint_id="ranged_terrain_read",
        cost=FeintCostDTO(tactics={"tempo": 1, "dodge": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_RANGED_TACTICAL_TAGS, "tempo", "dodge", "position_control", "anti_archer"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("ranged.close_weight_bonus", 0.15),
            pipeline_mutation("ranged.far_weight_bonus", -0.10),
        ],
    ),
}

_RANGED_TEXTS = {
    "reveal_intentions": (
        "Раскрыть намерения",
        "читая движение цели прочитать её вход по дистанции",
        "Тактический финт дальнего боя: читает вход цели и улучшает удержание средней/дальней позиции.",
        "читая движение цели по дистанции",
        "и заранее перестраивает линию отхода",
        "и превращает чтение входа в контроль дистанции",
    ),
    "covering_position": (
        "Позиция прикрытия",
        "занимая позицию под прикрытием стабилизировать позицию",
        "Тактический финт дальнего боя: снижает влияние давления и удерживает позицию не хуже средней.",
        "занимая позицию под прикрытием",
        "и оставляет путь для скользящего отхода",
        "и удерживает линию даже под давлением",
    ),
    "backstep_shot": (
        "Отстрел на отходе",
        "готовя выстрел на отходе сместиться на шаг назад",
        "Тактический финт дальнего боя: улучшает текущую позицию на один шаг и слегка усиливает точность выстрела.",
        "готовя выстрел на отходе",
        "и держит тетиву для ответного окна",
        "и переводит шаг назад в чистую линию выстрела",
    ),
    "open_distance": (
        "Разрыв дистанции",
        "разрывая дистанцию закрепить дальнюю позицию",
        "Тактический финт дальнего боя: поднимает текущую позицию минимум до средней и закрепляет дальнюю на следующий размен.",
        "разрывая дистанцию перед выстрелом",
        "и открывает предельное окно ответа",
        "и закрепляет дальнюю линию боя",
    ),
    "blinding_shot": (
        "Сбить темп входа",
        "целясь в ритм входа ослабить давление цели",
        "Тактический финт дальнего боя: мешает цели навязать ближнюю дистанцию в следующем позиционном расчете.",
        "целится в ритм входа цели",
        "и ломает темп сближения",
        "и оставляет цель без чистого входа",
    ),
    "ranged_terrain_read": (
        "Чтение местности",
        "читая местность сбить позицию противнику-лучнику",
        "Тактический финт дальнего боя: подталкивает противника-лучника к ближней позиции в следующем позиционном расчете.",
        "читая линию входа противника",
        "и сбивает позиционный выбор противника-лучника",
        "и затягивает противника-лучника на ближнюю линию",
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

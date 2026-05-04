from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
    default_feint_event_texts,
)
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintConfigDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

WEAPON_FEINTS_TECHNICAL = {
    "piercing_thrust": FeintTechnicalDTO(
        feint_id="piercing_thrust",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations={"formula.can_pierce": True},
    ),
    "shield_bash": FeintTechnicalDTO(
        feint_id="shield_bash",
        cost=FeintCostDTO(tactics={"block": 2}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["control.stun_on_hit"],
    ),
    "cleave": FeintTechnicalDTO(
        feint_id="cleave",
        cost=FeintCostDTO(tactics={"hit": 2, "crit": 1}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        raw_mutations={"physical_damage_mult": "-0.3"},
    ),
}

WEAPON_FEINTS_DESCRIPTIVE = {
    "piercing_thrust": build_combat_description(
        resource_type="feints",
        resource_id="piercing_thrust",
        display_name="Пронзающий выпад",
        short_description="Игнорирует броню цели.",
        humanoid_event_texts=default_feint_event_texts("Пронзающий выпад"),
        beast_event_texts=default_feint_event_texts("Пронзающий выпад"),
    ),
    "shield_bash": build_combat_description(
        resource_type="feints",
        resource_id="shield_bash",
        display_name="Удар щитом",
        short_description="Наносит урон и оглушает. Требует щит.",
        humanoid_event_texts=default_feint_event_texts("Удар щитом"),
        beast_event_texts=default_feint_event_texts("Удар щитом"),
    ),
    "cleave": build_combat_description(
        resource_type="feints",
        resource_id="cleave",
        display_name="Рассечение",
        short_description="Атакует несколько целей перед собой.",
        humanoid_long_description="Широкий рубящий удар по нескольким гуманоидным противникам перед исполнителем.",
        beast_display_name="Рассечение",
        beast_short_description="Широкий удар по зверю, рассчитанный на корпус, лапы или открытую шею.",
        beast_long_description="Широкое рассечение против зверя: исполнитель ведёт оружие по дуге, чтобы поймать рывок, корпус или конечности цели.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=[
                "{source} заносит оружие для широкого рассечения.",
                "{source} начинает рубящий замах по дуге в сторону {target}.",
                "{source} выбирает линию удара для рассечения перед собой.",
            ],
            hit=[
                "{source} рассекает {target} широким ударом.",
                "Рассечение {source} проходит по защите {target}.",
                "{target} получает рубящий удар от {source}.",
            ],
            crit=[
                "{source} глубоко рассекает {target}.",
                "Критическое рассечение {source} раскрывает защиту {target}.",
                "{target} не успевает закрыться от тяжёлой дуги {source}.",
            ],
            miss=[
                "{source} проводит рассечение мимо {target}.",
                "{target} выходит из линии рассечения {source}.",
            ],
            block=[
                "{target} принимает рассечение {source} на защиту.",
                "Удар {source} вязнет в блоке {target}.",
            ],
            parry=[
                "{target} парирует рассечение {source}.",
                "{target} сбивает дугу удара {source} в сторону.",
            ],
            dodge=[
                "{target} уходит из-под рассечения {source}.",
                "{target} отступает за пределы рубящей дуги {source}.",
            ],
            apply_effect=[
                "Рассечение {source} накладывает {effect} на {target}.",
            ],
            expire_effect=[
                "{effect} после рассечения на {target} заканчивается.",
            ],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[
                "{source} ведёт оружие широкой дугой против зверя {target}.",
                "{source} ловит рывок {target} и готовит рассечение.",
                "{source} смещается к боку {target}, раскрывая линию рубящего удара.",
            ],
            hit=[
                "{source} рассекает бок {target}.",
                "Рубящая дуга {source} цепляет {target}.",
                "{target} попадает под рассечение {source}.",
            ],
            crit=[
                "{source} глубоко рассекает открытую сторону {target}.",
                "Рассечение {source} тяжело проходит по {target}.",
                "{target} не успевает уйти от критической дуги {source}.",
            ],
            miss=[
                "{target} срывается с линии рассечения {source}.",
                "{source} рубит воздух там, где только что был {target}.",
            ],
            block=[
                "{target} принимает рассечение {source} плотной шкурой и массой.",
                "Удар {source} гаснет о корпус {target}.",
            ],
            parry=[
                "{target} сбивает рассечение {source} рывком корпуса.",
                "{target} уводит оружие {source} в сторону резким движением.",
            ],
            dodge=[
                "{target} отпрыгивает от рассечения {source}.",
                "{target} проскальзывает ниже рубящей дуги {source}.",
            ],
            apply_effect=[
                "Рассечение {source} оставляет {effect} на {target}.",
            ],
            expire_effect=[
                "{effect} после рассечения на {target} затухает.",
            ],
        ),
    ),
}

WEAPON_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=WEAPON_FEINTS_DESCRIPTIVE[feint_id],
    )
    for feint_id, technical in WEAPON_FEINTS_TECHNICAL.items()
}

WEAPON_FEINTS = [FeintConfigDTO.from_catalog_entry(entry) for entry in WEAPON_FEINTS_CATALOG.values()]

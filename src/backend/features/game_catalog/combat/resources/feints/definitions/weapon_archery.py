from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatDescriptionDTO,
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import pipeline_mutation
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

_ARCHERY_TAGS = ["weapon", "archery", "skill_archery", "ranged"]


WEAPON_ARCHERY_FEINTS_TECHNICAL = {
    "snap_shot": FeintTechnicalDTO(
        feint_id="snap_shot",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_ARCHERY_TAGS, "hit", "quick", "ignore_miss", "bonus_damage"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("ignore_miss")],
        hit_damage_bonus_per_tier=2,
    ),
    "headshot": FeintTechnicalDTO(
        feint_id="headshot",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_ARCHERY_TAGS, "hit", "crit", "crit_chance"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.30,
                tags=["archery", "aim"],
            )
        ],
    ),
    "piercing_arrow": FeintTechnicalDTO(
        feint_id="piercing_arrow",
        cost=FeintCostDTO(tactics={"hit": 5, "crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_ARCHERY_TAGS, "hit", "crit", "armor_penetration"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("boost_flat_armor_penetration"),
            pipeline_mutation("flat_armor_penetration_bonus_pct", 0.50),
        ],
    ),
    "precise_weak_spot": FeintTechnicalDTO(
        feint_id="precise_weak_spot",
        cost=FeintCostDTO(tactics={"crit": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_ARCHERY_TAGS, "crit", "forced_crit", "weapon_trigger"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("force.crit")],
    ),
    "quiet_weak_spot": FeintTechnicalDTO(
        feint_id="quiet_weak_spot",
        cost=FeintCostDTO(tactics={"hit": 2, "crit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_ARCHERY_TAGS, "crit", "forced_crit", "no_weapon_trigger", "damage"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("force.crit"),
            pipeline_mutation("crit_damage_boost"),
            pipeline_mutation("suppress_crit_triggers"),
        ],
    ),
    "arrow_fan": FeintTechnicalDTO(
        feint_id="arrow_fan",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 1}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.65,
        applicability_tags=[*_ARCHERY_TAGS, "hit", "crit", "damage", "multi_target"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.95)],
    ),
    "arrow_rain": FeintTechnicalDTO(
        feint_id="arrow_rain",
        cost=FeintCostDTO(tactics={"hit": 5, "crit": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.50,
        applicability_tags=[*_ARCHERY_TAGS, "hit", "crit", "damage", "multi_target", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.85),
            pipeline_mutation("suppress_crit_triggers"),
        ],
    ),
    "snap_shot_advanced": FeintTechnicalDTO(
        feint_id="snap_shot_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "tempo": 1}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_ARCHERY_TAGS, "hit", "tempo", "ignore_miss", "bonus_damage", "punish", "retreat"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("ignore_miss"),
            pipeline_mutation("ranged.current_position_step", 1),
        ],
        hit_damage_bonus_per_tier=2,
    ),
    "headshot_advanced": FeintTechnicalDTO(
        feint_id="headshot_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 2, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_ARCHERY_TAGS, "hit", "crit", "tempo", "crit_chance", "punish", "retreat"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.30,
                tags=["archery", "aim"],
            )
        ],
        pipeline_mutations=[pipeline_mutation("ranged.next_position_override", "far")],
    ),
    "piercing_arrow_advanced": FeintTechnicalDTO(
        feint_id="piercing_arrow_advanced",
        cost=FeintCostDTO(tactics={"hit": 5, "crit": 2, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_ARCHERY_TAGS, "hit", "crit", "tempo", "armor_penetration", "punish", "retreat"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("boost_flat_armor_penetration"),
            pipeline_mutation("flat_armor_penetration_bonus_pct", 0.50),
            pipeline_mutation("ranged.current_position_step", 1),
        ],
    ),
    "arrow_rain_advanced": FeintTechnicalDTO(
        feint_id="arrow_rain_advanced",
        cost=FeintCostDTO(tactics={"hit": 5, "crit": 2, "tempo": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.50,
        applicability_tags=[
            *_ARCHERY_TAGS,
            "hit",
            "crit",
            "tempo",
            "damage",
            "multi_target",
            "punish",
            "retreat",
            "high_cost",
        ],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.85),
            pipeline_mutation("suppress_crit_triggers"),
            pipeline_mutation("ranged.next_position_override", "far"),
        ],
    ),
    "ranged_covering_volley": FeintTechnicalDTO(
        feint_id="ranged_covering_volley",
        cost=FeintCostDTO(tactics={"hit": 4, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_ARCHERY_TAGS, "hit", "tempo", "position_damage", "covering_fire"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("ranged.outgoing_damage_bonus_mult", 1.20),
            pipeline_mutation("ranged.outgoing_accuracy_bonus_mult", 1.03),
            pipeline_mutation("ranged.far_weight_bonus", 0.10),
        ],
    ),
}

_ARCHERY_TEXTS = {
    "snap_shot": (
        "Быстрый выстрел",
        "выводя тетиву без паузы пустить стрелу",
        "Оружейный финт лука: надежный быстрый выстрел с небольшим бонусным уроном.",
        "выводя тетиву без полной остановки",
        "и выпускает стрелу по открытой линии",
        "и резко пробивает окно выстрела",
    ),
    "headshot": (
        "Выстрел в голову",
        "поднимая прицел выцелить голову",
        "Оружейный финт лука: следующий выстрел получает повышенный шанс крита.",
        "поднимая прицел выше защиты",
        "и ведет стрелу к голове цели",
        "и находит опасную верхнюю линию",
    ),
    "piercing_arrow": (
        "Пробивающая стрела",
        "натягивая тетиву пробить броню",
        "Оружейный финт лука: следующий выстрел получает усиленное пробитие брони.",
        "натягивая тетиву под тяжелый пробой",
        "и вгоняет стрелу в слабое место защиты",
        "и прошивает защитную линию",
    ),
    "precise_weak_spot": (
        "Точная слабая точка",
        "выбирая слабую точку открыть критический удар с триггером",
        "Оружейный финт лука: следующий выстрел критический и запускает стрелочный крит-триггер.",
        "выбирая слабую точку для стрелы",
        "и точно открывает слабую точку цели",
        "и дает стреле полностью раскрыть эффект",
    ),
    "quiet_weak_spot": (
        "Тихая слабая точка",
        "удерживая прицел провести крит без триггера",
        "Оружейный финт лука: следующий выстрел критический, без оружейного триггера, но с усиленным уроном.",
        "удерживая прицел до последнего момента",
        "и попадает в тихую слабую точку",
        "и превращает точность в чистый урон",
    ),
    "arrow_fan": (
        "Веер стрел",
        "натягивая тетиву выпустить веер стрел по трем целям",
        "Оружейный финт лука: основной выстрел задевает до двух дополнительных целей веером стрел.",
        "натягивая тетиву под широкий веер",
        "и разворачивает веер стрел по линии",
        "и накрывает три цели веером стрел",
    ),
    "arrow_rain": (
        "Град стрел",
        "выпуская стрелы дугой накрыть всех врагов",
        "Оружейный финт лука: основной выстрел расходится по всем врагам отголосками половинного урона.",
        "выпуская стрелы по широкой дуге",
        "и накрывает линию противников",
        "и превращает залп в опасный град",
    ),
    "snap_shot_advanced": (
        "Карательный быстрый выстрел",
        "наказывая промах противника пустить быстрый выстрел и отойти на шаг",
        "Карательный финт лука: тратит темп, надежный выстрел с бонусом и отход на шаг назад.",
        "наказывая промах противника",
        "и закрепляет шаг назад после выстрела",
        "и резко отрывается от противника после выстрела",
    ),
    "headshot_advanced": (
        "Карательный выстрел в голову",
        "наказывая ошибку противника выцелить голову и закрепить дальнюю позицию",
        "Карательный финт лука: тратит темп, повышает шанс крита и закрепляет дальнюю позицию.",
        "наказывая ошибку противника прицелом",
        "и точно бьет в голову и уходит на дальнюю линию",
        "и закрепляет дальнюю линию выстрелом в голову",
    ),
    "piercing_arrow_advanced": (
        "Карательное пробитие",
        "наказывая ошибку противника пробить броню и отойти на шаг",
        "Карательный финт лука: тратит темп, усиливает пробитие брони и сдвигает позицию на шаг назад.",
        "наказывая ошибку противника тяжелым пробоем",
        "и прошивает броню и закрепляет шаг назад",
        "и закрепляет шаг назад после пробития",
    ),
    "arrow_rain_advanced": (
        "Карательный град",
        "наказывая строй врагов накрыть всех и закрепить дальнюю позицию",
        "Карательный финт лука: тратит темп, накрывает всех врагов градом и закрепляет дальнюю позицию.",
        "наказывая строй противников широкой дугой",
        "и накрывает строй и уходит на дальнюю линию",
        "и закрепляет дальнюю линию после града стрел",
    ),
    "ranged_covering_volley": (
        "Огневое прикрытие",
        "держа цель под прикрывающим огнем раскрыть позиционный выстрел",
        "Оружейный финт лука: усиливает бонус удобной позиции и снижает штраф неудобной позиции к выстрелу.",
        "держа цель под прикрывающим огнем",
        "и раскрывает позиционную линию выстрела",
        "и превращает позицию в плотный огонь",
    ),
}


def _archery_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _ARCHERY_TEXTS[feint_id]
    return build_combat_description(
        resource_type="feints",
        resource_id=feint_id,
        icon=f"combat/feints/{feint_id}.svg",
        display_name=display_name,
        ui_label=ui_label,
        short_description=short,
        humanoid_long_description=short,
        humanoid_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} целится в {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но стрела проходит мимо"],
            dodge=["но {target} уходит с линии выстрела"],
            parry=["но {target} сбивает траекторию"],
            block=["но {target} закрывается от стрелы"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} целится в {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но стрела проходит мимо"],
            dodge=["но {target} уходит с линии выстрела"],
            parry=["но {target} сбивает траекторию движением"],
            block=["но стрела гаснет о защиту {target}"],
        ),
    )


WEAPON_ARCHERY_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_archery_description(feint_id),
    )
    for feint_id, technical in WEAPON_ARCHERY_FEINTS_TECHNICAL.items()
}

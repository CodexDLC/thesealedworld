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
}

_ARCHERY_TEXTS = {
    "snap_shot": (
        "Быстрый выстрел",
        "Пустить стрелу без паузы",
        "Оружейный финт лука: надежный быстрый выстрел с небольшим бонусным уроном.",
        "выводя тетиву без полной остановки",
        "и выпускает стрелу по открытой линии",
        "и резко пробивает окно выстрела",
    ),
    "headshot": (
        "Выстрел в голову",
        "Открыть критовое окно",
        "Оружейный финт лука: следующий выстрел получает повышенный шанс крита.",
        "поднимая прицел выше защиты",
        "и ведет стрелу к голове цели",
        "и находит опасную верхнюю линию",
    ),
    "piercing_arrow": (
        "Пробивающая стрела",
        "Пробить броню",
        "Оружейный финт лука: следующий выстрел получает усиленное пробитие брони.",
        "натягивая тетиву под тяжелый пробой",
        "и вгоняет стрелу в слабое место защиты",
        "и прошивает защитную линию",
    ),
    "precise_weak_spot": (
        "Точная слабая точка",
        "Крит с триггером стрелы",
        "Оружейный финт лука: следующий выстрел критический и запускает стрелочный крит-триггер.",
        "выбирая слабую точку для стрелы",
        "и точно открывает слабую точку цели",
        "и дает стреле полностью раскрыть эффект",
    ),
    "quiet_weak_spot": (
        "Тихая слабая точка",
        "Крит без триггера",
        "Оружейный финт лука: следующий выстрел критический, без оружейного триггера, но с усиленным уроном.",
        "удерживая прицел до последнего момента",
        "и попадает в тихую слабую точку",
        "и превращает точность в чистый урон",
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

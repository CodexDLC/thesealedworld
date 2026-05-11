from src.backend.features.game_catalog.combat.resources.common.descriptions import (
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

_TECHNIQUE_TAGS = ["weapon", "weapon_technique", "ignore_miss", "bonus_damage"]

WEAPON_TECHNIQUES_TECHNICAL = {
    "measured_strike": FeintTechnicalDTO(
        feint_id="measured_strike",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=[pipeline_mutation("ignore_miss")],
        applicability_tags=[*_TECHNIQUE_TAGS, "tier_1"],
        hit_damage_bonus_per_tier=3,
    ),
    "steady_strike": FeintTechnicalDTO(
        feint_id="steady_strike",
        cost=FeintCostDTO(tactics={"hit": 5}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=[pipeline_mutation("ignore_miss")],
        applicability_tags=[*_TECHNIQUE_TAGS, "tier_2"],
        hit_damage_bonus_per_tier=5,
    ),
    "flawless_strike": FeintTechnicalDTO(
        feint_id="flawless_strike",
        cost=FeintCostDTO(tactics={"hit": 7}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=[pipeline_mutation("ignore_miss")],
        applicability_tags=[*_TECHNIQUE_TAGS, "tier_3"],
        hit_damage_bonus_per_tier=7,
    ),
    "decisive_attack": FeintTechnicalDTO(
        feint_id="decisive_attack",
        cost=FeintCostDTO(tactics={"hit": 9}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=[pipeline_mutation("ignore_miss")],
        applicability_tags=[*_TECHNIQUE_TAGS, "tier_4"],
        hit_damage_bonus_per_tier=9,
    ),
}

_WEAPON_TECHNIQUE_TEXTS = {
    "measured_strike": ("Выверенный удар", "Спокойно провести оружейную атаку", "Выверенный прием с бонусным уроном."),
    "steady_strike": (
        "Уверенный удар",
        "Закрепить темп и провести атаку",
        "Уверенный прием с большим бонусным уроном.",
    ),
    "flawless_strike": ("Безошибочный удар", "Не отпустить линию атаки", "Дорогой прием с высоким бонусным уроном."),
    "decisive_attack": (
        "Решающая атака",
        "Вложить накопленный темп в удар",
        "Очень дорогой прием с большим бонусным уроном.",
    ),
}


def _description(feint_id: str) -> object:
    display_name, ui_label, short = _WEAPON_TECHNIQUE_TEXTS[feint_id]
    return build_combat_description(
        resource_type="feints",
        resource_id=feint_id,
        icon=f"combat/feints/{feint_id}.svg",
        display_name=display_name,
        ui_label=ui_label,
        short_description=short,
        humanoid_long_description=short,
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} выбирает момент и проводит {weapon_attack_form} по {target}"],
            hit=["и доводит {weapon_attack_line}, добавляя {bonus_damage} урона"],
            crit=["и точно раскрывает {weapon_attack_line}, добавляя {bonus_damage} урона"],
            miss=["но атака не находит результата"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} отводит атаку"],
            block=["но {target} закрывает линию защиты"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} выбирает момент и проводит {weapon_attack_form} по {target}"],
            hit=["и доводит {weapon_attack_line}, добавляя {bonus_damage} урона"],
            crit=["и точно раскрывает {weapon_attack_line}, добавляя {bonus_damage} урона"],
            miss=["но атака не находит результата"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} сбивает атаку движением"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


WEAPON_TECHNIQUES_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_description(feint_id),
    )
    for feint_id, technical in WEAPON_TECHNIQUES_TECHNICAL.items()
}

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

_BASIC_HIT_TAGS = ["basic", "hit", "weapon", "weapon_technique", "ignore_miss", "bonus_damage"]


BASIC_HIT_FEINTS_TECHNICAL = {
    "measured_strike": FeintTechnicalDTO(
        feint_id="measured_strike",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=[pipeline_mutation("ignore_miss")],
        applicability_tags=[*_BASIC_HIT_TAGS, "tier_1"],
        hit_damage_bonus_per_tier=2,
    ),
    "steady_strike": FeintTechnicalDTO(
        feint_id="steady_strike",
        cost=FeintCostDTO(tactics={"hit": 5}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=[pipeline_mutation("ignore_miss")],
        applicability_tags=[*_BASIC_HIT_TAGS, "tier_2"],
        hit_damage_bonus_per_tier=4,
    ),
    "flawless_strike": FeintTechnicalDTO(
        feint_id="flawless_strike",
        cost=FeintCostDTO(tactics={"hit": 7}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=[pipeline_mutation("ignore_miss")],
        applicability_tags=[*_BASIC_HIT_TAGS, "tier_3"],
        hit_damage_bonus_per_tier=5,
    ),
    "measured_strike_advanced": FeintTechnicalDTO(
        feint_id="measured_strike_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "tempo": 1}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=[pipeline_mutation("ignore_miss")],
        applicability_tags=[*_BASIC_HIT_TAGS, "tempo", "tier_1", "punish"],
        hit_damage_bonus_per_tier=2,
        effects=[{"id": "debuff_accuracy", "target_actor": "target"}],
    ),
}

_BASIC_HIT_TEXTS = {
    "measured_strike": (
        "Выверенный удар",
        "спокойно провести оружейную атаку",
        "Базовый hit-финт: надежный удар с бонусным уроном.",
    ),
    "steady_strike": (
        "Уверенный удар",
        "закрепляя линию провести атаку",
        "Базовый hit-финт: усиленный надежный удар.",
    ),
    "flawless_strike": (
        "Безошибочный удар",
        "не отпуская линию довести атаку до конца",
        "Базовый hit-финт: дорогой надежный удар с высоким бонусным уроном.",
    ),
    "measured_strike_advanced": (
        "Карательный выверенный удар",
        "наказывая промах противника провести надежный удар и сбить ему точность",
        "Карательный базовый hit-финт: тратит темп, надежный удар с бонусом и сбивает точность цели.",
    ),
}


def _basic_hit_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short = _BASIC_HIT_TEXTS[feint_id]
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


BASIC_HIT_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_basic_hit_description(feint_id),
    )
    for feint_id, technical in BASIC_HIT_FEINTS_TECHNICAL.items()
}

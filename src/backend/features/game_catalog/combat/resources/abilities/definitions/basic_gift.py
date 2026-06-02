from src.backend.features.game_catalog.combat.resources.abilities.enums import AbilitySource, AbilityType
from src.backend.features.game_catalog.combat.resources.abilities.schemas import (
    AbilityCatalogEntryDTO,
    AbilityCostDTO,
    AbilityTechnicalDTO,
    PipelineMutationsDTO,
)
from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import pipeline_mutation
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType

BASIC_GIFT_ABILITY_IDS: tuple[str, ...] = (
    "basic_punish_mistake",
    "basic_finish_moment",
    "basic_break_stance",
    "basic_expose_weakness",
    "basic_wipe_blood",
    "basic_grit_teeth",
    "basic_bloody_answer",
    "basic_last_push",
)

_TACTICAL_INSTANT_STRIKE = PipelineMutationsDTO(
    preset="TACTICAL_INSTANT_STRIKE",
    applications=[
        pipeline_mutation("damage.physical", True),
        pipeline_mutation("damage.arcane", False),
        pipeline_mutation("damage_mult", 1.2),
    ],
)


BASIC_GIFT_ABILITIES_TECHNICAL: dict[str, AbilityTechnicalDTO] = {
    "basic_punish_mistake": AbilityTechnicalDTO(
        ability_id="basic_punish_mistake",
        source=AbilitySource.COMBAT,
        type=AbilityType.INSTANT,
        cost=AbilityCostDTO(energy=10, tokens={"tempo": 2, "hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=_TACTICAL_INSTANT_STRIKE,
        ai_tags=["tempo", "hit", "damage", "single_target"],
    ),
    "basic_finish_moment": AbilityTechnicalDTO(
        ability_id="basic_finish_moment",
        source=AbilitySource.COMBAT,
        type=AbilityType.INSTANT,
        cost=AbilityCostDTO(energy=10, tokens={"tempo": 2, "crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=_TACTICAL_INSTANT_STRIKE,
        ai_tags=["tempo", "crit", "damage", "execute"],
    ),
    "basic_break_stance": AbilityTechnicalDTO(
        ability_id="basic_break_stance",
        source=AbilitySource.COMBAT,
        type=AbilityType.INSTANT,
        cost=AbilityCostDTO(energy=10, tokens={"tempo": 2, "hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=_TACTICAL_INSTANT_STRIKE,
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="physical_damage_bonus_add",
                target_actor="target",
                value_mode="source_main_hand_damage_multiplier",
                value_multiplier=-0.25,
                value_override=1.2,
                scope="duration",
                duration_exchanges=4,
            )
        ],
        ai_tags=["tempo", "hit", "debuff", "anti_defense"],
    ),
    "basic_expose_weakness": AbilityTechnicalDTO(
        ability_id="basic_expose_weakness",
        source=AbilitySource.COMBAT,
        type=AbilityType.INSTANT,
        cost=AbilityCostDTO(energy=10, tokens={"tempo": 2, "crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=_TACTICAL_INSTANT_STRIKE,
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="evasion_add",
                target_actor="target",
                value_override=-0.5,
                scope="duration",
                duration_exchanges=3,
            )
        ],
        ai_tags=["tempo", "crit", "debuff", "anti_evasion"],
    ),
    "basic_wipe_blood": AbilityTechnicalDTO(
        ability_id="basic_wipe_blood",
        source=AbilitySource.COMBAT,
        type=AbilityType.INSTANT,
        cost=AbilityCostDTO(energy=10, tokens={"blood": 1}),
        target=TargetType.SELF,
        pipeline_mutations=PipelineMutationsDTO(preset="HEALING"),
        override_damage=(6.0, 10.0),
        ai_tags=["blood", "heal", "self"],
    ),
    "basic_grit_teeth": AbilityTechnicalDTO(
        ability_id="basic_grit_teeth",
        source=AbilitySource.COMBAT,
        type=AbilityType.INSTANT,
        cost=AbilityCostDTO(energy=10, tokens={"blood": 1}),
        target=TargetType.SELF,
        pipeline_mutations=PipelineMutationsDTO(preset="BUFF"),
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="armor_add",
                target_actor="self",
                value_override=6.0,
                scope="duration",
                duration_exchanges=2,
            )
        ],
        ai_tags=["blood", "defense", "self_buff"],
    ),
    "basic_bloody_answer": AbilityTechnicalDTO(
        ability_id="basic_bloody_answer",
        source=AbilitySource.COMBAT,
        type=AbilityType.INSTANT,
        cost=AbilityCostDTO(energy=10, tokens={"blood": 1, "hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=_TACTICAL_INSTANT_STRIKE,
        effects=[{"id": "dot_bleed", "params": {"duration": 2, "power": 0.75, "apply_bonus": 0.25}}],
        ai_tags=["blood", "hit", "damage", "bleed"],
    ),
    "basic_last_push": AbilityTechnicalDTO(
        ability_id="basic_last_push",
        source=AbilitySource.COMBAT,
        type=AbilityType.INSTANT,
        cost=AbilityCostDTO(energy=10, tokens={"blood": 1, "tempo": 2}),
        target=TargetType.SELF,
        pipeline_mutations=PipelineMutationsDTO(preset="HEALING"),
        override_damage=(8.0, 12.0),
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="physical_damage_bonus_add",
                target_actor="self",
                value_override=3.0,
                scope="duration",
                duration_exchanges=2,
            )
        ],
        ai_tags=["blood", "tempo", "heal", "self_buff"],
    ),
}


BASIC_GIFT_ABILITIES_DESCRIPTIVE = {
    "basic_punish_mistake": build_combat_description(
        resource_type="abilities",
        resource_id="basic_punish_mistake",
        icon="combat/abilities/basic_punish_mistake.svg",
        display_name="Наказать ошибку",
        ui_label="Наказать ошибку",
        short_description="Тратит темп и попадание, чтобы нанести быстрый урон.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} ловит ошибку {target}."],
            hit=["удар в окно наказывает {target}"],
            crit=["{source} превращает ошибку {target} в резкий перелом"],
            miss=["{target} успевает закрыть ошибку"],
            no_resource=["{source} видит ошибку, но не успевает её наказать"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "basic_finish_moment": build_combat_description(
        resource_type="abilities",
        resource_id="basic_finish_moment",
        icon="combat/abilities/basic_finish_moment.svg",
        display_name="Добить момент",
        ui_label="Добить момент",
        short_description="Тратит темп и критический момент на удар по открытому моменту.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} вкладывает критический момент в удар по {target}."],
            hit=["момент обрушивается на {target}"],
            crit=["{source} добивает открытый момент {target}"],
            miss=["момент срывается до удара"],
            no_resource=["{source} пытается дожать момент, но ресурсов не хватает"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "basic_break_stance": build_combat_description(
        resource_type="abilities",
        resource_id="basic_break_stance",
        icon="combat/abilities/basic_break_stance.svg",
        display_name="Сбить стойку",
        ui_label="Сбить стойку",
        short_description="Тратит темп и попадание, чтобы ослабить защитную стойку цели.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} сбивает стойку {target}."],
            hit=["{source} ломает устойчивость {target}"],
            apply_effect=["{target} теряет устойчивость: {effect}."],
            no_resource=["{source} не удерживает темп для сбития стойки"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "basic_expose_weakness": build_combat_description(
        resource_type="abilities",
        resource_id="basic_expose_weakness",
        icon="combat/abilities/basic_expose_weakness.svg",
        display_name="Открыть слабость",
        ui_label="Открыть слабость",
        short_description="Тратит темп и критический момент, чтобы подавить уклонение цели.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} отмечает слабое место {target}."],
            hit=["{source} бьёт в слабое место {target}"],
            apply_effect=["слабость {target} открыта: {effect}."],
            no_resource=["{source} видит слабость, но не может её открыть"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "basic_wipe_blood": build_combat_description(
        resource_type="abilities",
        resource_id="basic_wipe_blood",
        icon="combat/abilities/basic_wipe_blood.svg",
        display_name="Утереть кровь",
        ui_label="Утереть кровь",
        short_description="Тратит кровь, чтобы восстановить часть здоровья.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} заставляет кровь работать на выживание."],
            heal=["{source} собирается и закрывает раны"],
            no_resource=["{source} не находит в боли достаточно силы"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "basic_grit_teeth": build_combat_description(
        resource_type="abilities",
        resource_id="basic_grit_teeth",
        icon="combat/abilities/basic_grit_teeth.svg",
        display_name="Стиснуть зубы",
        ui_label="Стиснуть зубы",
        short_description="Тратит кровь, чтобы усилить броню на короткое время.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} сжимает боль в защиту."],
            apply_effect=["{source} получает {effect}."],
            no_resource=["{source} не может собрать боль в защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "basic_bloody_answer": build_combat_description(
        resource_type="abilities",
        resource_id="basic_bloody_answer",
        icon="combat/abilities/basic_bloody_answer.svg",
        display_name="Кровавый ответ",
        ui_label="Кровавый ответ",
        short_description="Тратит кровь и попадание, чтобы ударить в ответ и открыть кровотечение.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} отвечает болью по {target}."],
            hit=["кровавый ответ достаёт {target}"],
            apply_effect=["рана {target} открывается: {effect}."],
            no_resource=["{source} не может превратить боль в ответ"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "basic_last_push": build_combat_description(
        resource_type="abilities",
        resource_id="basic_last_push",
        icon="combat/abilities/basic_last_push.svg",
        display_name="Последний рывок",
        ui_label="Последний рывок",
        short_description="Тратит кровь и темп, чтобы восстановиться и усилиться на короткое время.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} выжимает из себя последний рывок."],
            heal=["{source} возвращает себе часть сил"],
            apply_effect=["рывок усиливает {source}: {effect}."],
            no_resource=["{source} не находит сил для последнего рывка"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
}


BASIC_GIFT_ABILITIES_CATALOG = {
    ability_id: AbilityCatalogEntryDTO(
        key=f"combat.ability.{ability_id}",
        technical=technical,
        descriptive=BASIC_GIFT_ABILITIES_DESCRIPTIVE[ability_id],
    )
    for ability_id, technical in BASIC_GIFT_ABILITIES_TECHNICAL.items()
}

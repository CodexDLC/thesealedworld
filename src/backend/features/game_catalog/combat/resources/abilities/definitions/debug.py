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

ABILITIES_TECHNICAL = {
    # ==========================================================================
    # 1. FIREBALL (Магическая Атака)
    # ==========================================================================
    "fireball": AbilityTechnicalDTO(
        ability_id="fireball",
        source=AbilitySource.GIFT,
        type=AbilityType.INSTANT,
        # Стоит ману и 1 токен дара
        cost=AbilityCostDTO(energy=25, gift_tokens=1),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=PipelineMutationsDTO(
            preset="MAGIC_ATTACK",
            applications=[
                pipeline_mutation("damage.fire", True),
                pipeline_mutation("damage.physical", False),
            ],
        ),
        override_damage=(40.0, 60.0),
        modifier_applications=[
            ModifierApplicationDTO(modifier_id="damage_mult", value_override=0.5),
        ],
        triggers=["crit.burn_on_crit"],
    ),
    # ==========================================================================
    # 2. HEAL (Лечение)
    # ==========================================================================
    "heal": AbilityTechnicalDTO(
        ability_id="heal",
        source=AbilitySource.GIFT,
        type=AbilityType.INSTANT,
        # Стоит меньше маны, но тоже требует токен
        cost=AbilityCostDTO(energy=15, gift_tokens=1),
        target=TargetType.SINGLE_ALLY,
        pipeline_mutations=PipelineMutationsDTO(preset="HEALING"),
        override_damage=(50.0, 60.0),
        effects=[{"id": "cleanse_bleed", "params": {}}],
    ),
    # ==========================================================================
    # 3. STONE SKIN (Бафф)
    # ==========================================================================
    "stone_skin": AbilityTechnicalDTO(
        ability_id="stone_skin",
        source=AbilitySource.GIFT,
        type=AbilityType.INSTANT,
        # Мощный бафф, стоит 2 токена (КД 2 хода)
        cost=AbilityCostDTO(energy=30, gift_tokens=2),
        target=TargetType.SELF,
        pipeline_mutations=PipelineMutationsDTO(preset="BUFF"),
        effects=[{"id": "buff_armor", "params": {"duration": 3, "value": 20, "stat": "damage_reduction_flat"}}],
    ),
    # ==========================================================================
    # 4. TRUE STRIKE (Атака без пресета)
    # ==========================================================================
    "true_strike_spell": AbilityTechnicalDTO(
        ability_id="true_strike_spell",
        source=AbilitySource.GIFT,
        type=AbilityType.INSTANT,
        # Дешевый спелл
        cost=AbilityCostDTO(energy=10, gift_tokens=1),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=PipelineMutationsDTO(
            applications=[
                pipeline_mutation("meta.source_type", "magic"),
                pipeline_mutation("stage.check_accuracy", True),
                pipeline_mutation("stage.check_evasion", False),
                pipeline_mutation("stage.check_parry", False),
                pipeline_mutation("stage.check_block", True),
                pipeline_mutation("stage.calculate_damage", True),
                pipeline_mutation("ignore_evasion"),
            ]
        ),
        override_damage=(20.0, 25.0),
    ),
}


ABILITIES_DESCRIPTIVE = {
    "fireball": build_combat_description(
        resource_type="abilities",
        resource_id="fireball",
        icon="combat/abilities/fireball.svg",
        display_name="Огненный Шар",
        ui_label="Бросить огненный шар",
        short_description="Наносит урон огнем и поджигает цель.",
        humanoid_long_description="Сгусток живого пламени, который ударяет по цели и может оставить ожог.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} бросает {ability} в сторону {target}"],
            hit=["пламя ударяет в {target}"],
            crit=["{ability} взрывается у {target} особенно ярко"],
            miss=["но огонь проходит мимо {target}"],
            apply_effect=["пламя цепляется за {target}, оставляя {effect}"],
            area_use=["{source} бросает {ability}"],
            area_result=["пламя расходится по {targets_count} целям"],
            no_resource=["{source} пытается собрать {ability}, но жар гаснет раньше броска"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "heal": build_combat_description(
        resource_type="abilities",
        resource_id="heal",
        icon="combat/abilities/heal.svg",
        display_name="Исцеление",
        ui_label="Исцелить союзника",
        short_description="Восстанавливает здоровье союзнику.",
        humanoid_long_description="Мягкий поток дара закрывает раны и возвращает телу устойчивость.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} направляет {ability} на {target}"],
            heal=["{source} направляет {ability} на {target}"],
            apply_effect=["чистая энергия {ability} снимает с {target} эффект {effect}"],
            no_resource=["{source} тянется к {ability}, но сил не хватает"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "stone_skin": build_combat_description(
        resource_type="abilities",
        resource_id="stone_skin",
        icon="combat/abilities/stone_skin.svg",
        display_name="Каменная Кожа",
        ui_label="Укрепить кожу камнем",
        short_description="Повышает броню на 3 хода.",
        humanoid_long_description="Кожа грубеет и покрывается плотной каменной коркой, принимая часть удара на себя.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} сгущает землю под кожей"],
            apply_effect=["{source} покрывает кожу каменной коркой"],
            no_resource=["{source} пытается поднять каменную защиту, но земля не отзывается"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "true_strike_spell": build_combat_description(
        resource_type="abilities",
        resource_id="true_strike_spell",
        icon="combat/abilities/true_strike_spell.svg",
        display_name="Верный Выстрел",
        ui_label="Пустить неуклонную стрелу",
        short_description="Магическая стрела, от которой нельзя увернуться.",
        humanoid_long_description="Короткая магическая стрела выбирает прямую линию и почти не оставляет цели места для ухода.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} вытягивает линию {ability} к {target}"],
            hit=["{ability} находит прямую линию к {target}"],
            crit=["{ability} прошивает защитный ритм {target}"],
            miss=["линия {ability} рвется до удара по {target}"],
            no_resource=["{source} не удерживает линию {ability}: ресурса не хватает"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
}


ABILITIES_CATALOG = {
    ability_id: AbilityCatalogEntryDTO(
        key=f"combat.ability.{ability_id}",
        technical=technical,
        descriptive=ABILITIES_DESCRIPTIVE[ability_id],
    )
    for ability_id, technical in ABILITIES_TECHNICAL.items()
}

ABILITIES_DEFINITIONS = {ability_id: entry.technical for ability_id, entry in ABILITIES_CATALOG.items()}

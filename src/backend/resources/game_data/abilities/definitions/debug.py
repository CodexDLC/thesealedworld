from src.backend.resources.game_data.abilities.enums import AbilitySource, AbilityType
from src.backend.resources.game_data.abilities.schemas import (
    AbilityConfigDTO,
    AbilityCostDTO,
    PipelineMutationsDTO,
)
from src.backend.resources.game_data.common.targeting import TargetType

# Словарь способностей (ID -> DTO)
ABILITIES_DEFINITIONS = {
    # ==========================================================================
    # 1. FIREBALL (Магическая Атака)
    # ==========================================================================
    "fireball": AbilityConfigDTO(
        ability_id="fireball",
        name_ru="Огненный Шар",
        description_ru="Наносит урон огнем и поджигает цель.",
        source=AbilitySource.GIFT,
        type=AbilityType.INSTANT,
        # Стоит ману и 1 токен дара
        cost=AbilityCostDTO(energy=25, gift_tokens=1),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=PipelineMutationsDTO(
            preset="MAGIC_ATTACK",
            flags={
                "damage.fire": True,
                "damage.physical": False,
            },
        ),
        override_damage=(40.0, 60.0),
        raw_mutations={"magical_damage_mult": "*1.5"},
        triggers=["crit.burn_on_crit"],
    ),
    # ==========================================================================
    # 2. HEAL (Лечение)
    # ==========================================================================
    "heal": AbilityConfigDTO(
        ability_id="heal",
        name_ru="Исцеление",
        description_ru="Восстанавливает здоровье союзнику.",
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
    "stone_skin": AbilityConfigDTO(
        ability_id="stone_skin",
        name_ru="Каменная Кожа",
        description_ru="Повышает броню на 3 хода.",
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
    "true_strike_spell": AbilityConfigDTO(
        ability_id="true_strike_spell",
        name_ru="Верный Выстрел",
        description_ru="Магическая стрела, от которой нельзя увернуться.",
        source=AbilitySource.GIFT,
        type=AbilityType.INSTANT,
        # Дешевый спелл
        cost=AbilityCostDTO(energy=10, gift_tokens=1),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=PipelineMutationsDTO(
            flags={
                "meta.source_type": "magic",
                "stages.check_accuracy": True,
                "stages.check_evasion": False,
                "stages.check_parry": False,
                "stages.check_block": True,
                "stages.calculate_damage": True,
                "force.hit_evasion": True,
            }
        ),
        override_damage=(20.0, 25.0),
    ),
}

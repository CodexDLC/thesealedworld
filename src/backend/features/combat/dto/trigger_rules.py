"""
DTO для флагов активации правил триггеров (Trigger Rules).
Структурировано по этапам резолвера для оптимизации поиска.
"""

from pydantic import BaseModel, Field


class AccuracyTriggersDTO(BaseModel):
    """Триггеры этапа Точности (ON_ACCURACY_CHECK, ON_MISS)."""

    true_strike: bool = False  # Игнор уворота
    rage_on_miss: bool = False  # Бонус при промахе

    # Styles
    style_2h_ignore: bool = False  # Игнор брони + Дебафф
    style_dual_extra: bool = False  # Доп. атака


class CritTriggersDTO(BaseModel):
    """Триггеры этапа Крита (ON_CRIT, ON_CRIT_FAIL)."""

    weapon_serrated_bleed_crit: bool = False
    weapon_heavy_crit: bool = False
    weapon_impact_stun_crit: bool = False
    weapon_piercing_crit: bool = False
    weapon_flat_armor_gap_crit: bool = False
    weapon_flat_armor_bypass_crit: bool = False
    weapon_flat_armor_crush_crit: bool = False
    weapon_precision_crit: bool = False
    weapon_shieldbreaker_crit: bool = False


class DodgeTriggersDTO(BaseModel):
    """Триггеры этапа Уклонения (ON_DODGE, ON_DODGE_FAIL)."""

    counter_on_dodge: bool = False
    style_ranged_perfect_backstep: bool = False


class ParryTriggersDTO(BaseModel):
    """Триггеры этапа Парирования (ON_PARRY, ON_PARRY_FAIL)."""

    weapon_riposte_on_parry: bool = False


class BlockTriggersDTO(BaseModel):
    """Триггеры этапа Блока (ON_BLOCK, ON_BLOCK_FAIL)."""

    weapon_shield_bash_on_block: bool = False

    # Styles
    style_shield_reflect: bool = False  # Отражение урона


class ControlTriggersDTO(BaseModel):
    """Триггеры финального этапа (ON_CHECK_CONTROL)."""

    weapon_serrated_bleed_hit: bool = False
    weapon_knockdown_hit: bool = False
    weapon_evasive_shot: bool = False


class DamageTriggersDTO(BaseModel):
    """Триггеры этапа расчета урона (ON_DAMAGE)."""

    execute_low_hp: bool = False


class TriggerRulesFlagsDTO(BaseModel):
    """
    Корневой DTO для флагов триггеров.
    Используется в PipelineContextDTO.
    """

    accuracy: AccuracyTriggersDTO = Field(default_factory=AccuracyTriggersDTO)
    crit: CritTriggersDTO = Field(default_factory=CritTriggersDTO)

    dodge: DodgeTriggersDTO = Field(default_factory=DodgeTriggersDTO)
    parry: ParryTriggersDTO = Field(default_factory=ParryTriggersDTO)
    block: BlockTriggersDTO = Field(default_factory=BlockTriggersDTO)

    control: ControlTriggersDTO = Field(default_factory=ControlTriggersDTO)
    damage: DamageTriggersDTO = Field(default_factory=DamageTriggersDTO)

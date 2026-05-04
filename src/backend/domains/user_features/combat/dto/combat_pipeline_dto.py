"""
DTO для управления Пайплайном Боя (Combat Pipeline).
Содержит флаги, контексты и результаты расчетов.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.backend.domains.user_features.combat.dto.trigger_rules_flags_dto import TriggerRulesFlagsDTO

# ==============================================================================
# 1. FLAGS & SWITCHES (Управление логикой)
# ==============================================================================


class PipelinePhasesDTO(BaseModel):
    """Управление глобальными фазами пайплайна."""

    run_pre_calc: bool = True
    run_stats_engine: bool = True  # NEW: Отдельный флаг для статов
    run_calculator: bool = True
    run_post_calc: bool = True

    is_target_dead: bool = False


class ForceFlagsDTO(BaseModel):
    """Абсолютные переключатели результата."""

    hit: bool = False
    miss: bool = False
    crit: bool = False
    dodge: bool = False
    parry: bool = False
    block: bool = False
    hit_evasion: bool = False


class RestrictionFlagsDTO(BaseModel):
    """Запреты."""

    cannot_crit: bool = False
    ignore_parry: bool = False
    ignore_block: bool = False


class MasteryFlagsDTO(BaseModel):
    """Флаги мастерства."""

    light_armor: bool = False
    medium_armor: bool = False
    shield_reflect: bool = False
    unarmed_combo: bool = False


class FormulaFlagsDTO(BaseModel):
    """Переключатели формул."""

    # Evasion
    evasion_halved: bool = False
    ignore_evasion_cap: bool = False
    zero_anti_evasion: bool = False

    # Parry/Block
    parry_halved: bool = False
    ignore_parry_cap: bool = False
    block_halved: bool = False
    ignore_block_cap: bool = False

    # Crit
    crit_ignore_anticrit: bool = False
    crit_damage_boost: bool = False  # Включает повышенный урон при крите

    # Damage
    can_pierce: bool = False  # Разрешить проверку на пронзание

    # Counter Attack
    counter_chance_boost: bool = False  # Был enable_counter (+20% chance)


class DamageTypeFlagsDTO(BaseModel):
    """Типы урона."""

    physical: bool = True
    pure: bool = False
    fire: bool = False
    water: bool = False
    air: bool = False
    earth: bool = False
    light: bool = False
    darkness: bool = False
    arcane: bool = False
    nature: bool = False
    healing: bool = False  # NEW: Тип урона "Лечение"


class StateFlagsDTO(BaseModel):
    """Внутреннее состояние."""

    partial_absorb_reflect: bool = False
    is_reflect_block: bool = False
    open_combo: bool = False
    hit_index: int = 0

    # Counter Attack State
    allow_counter_on_parry: bool = False  # Был can_counter_on_parry
    check_counter: bool = False  # Сигнал для запуска этапа проверки контратаки


class MetaFlagsDTO(BaseModel):
    """Строковые мета-данные и счетчики."""

    source_type: Literal["main_hand", "off_hand", "magic", "item"] = "main_hand"
    weapon_class: str | None = None  # swords, macing, unarmed...
    crit_trigger_key: str | None = None  # stun, bleed...
    attack_index: int = 0
    combo_stage: int = 0

    # Context Flags (для Executor)
    has_offhand_weapon: bool = False

    # Режим действия (Exchange / Unidirectional)
    action_mode: Literal["exchange", "unidirectional"] = "exchange"


class MechanicsFlagsDTO(BaseModel):
    """
    Мутация стейта (Mechanics Service).
    Управляет тем, какие изменения применяются к акторам.
    """

    pay_cost: bool = True  # Списывать ли энергию/хп за действие
    grant_xp: bool = True  # Начислять ли опыт в буфер
    check_death: bool = True  # Проверять ли смерть после удара
    apply_damage: bool = True  # Наносить ли урон в HP/Shield
    apply_sustain: bool = True  # Считать ли вампиризм/реген
    apply_periodic: bool = False  # Флаг для тиков DoT/HoT
    generate_feints: bool = True  # NEW: Генерировать ли финты (отключать для insta_skill)


class PipelineFlagsDTO(BaseModel):
    """Группировка всех флагов."""

    force: ForceFlagsDTO = Field(default_factory=ForceFlagsDTO)
    restriction: RestrictionFlagsDTO = Field(default_factory=RestrictionFlagsDTO)
    mastery: MasteryFlagsDTO = Field(default_factory=MasteryFlagsDTO)
    formula: FormulaFlagsDTO = Field(default_factory=FormulaFlagsDTO)
    damage: DamageTypeFlagsDTO = Field(default_factory=DamageTypeFlagsDTO)
    state: StateFlagsDTO = Field(default_factory=StateFlagsDTO)
    meta: MetaFlagsDTO = Field(default_factory=MetaFlagsDTO)
    mechanics: MechanicsFlagsDTO = Field(default_factory=MechanicsFlagsDTO)  # NEW


# ==============================================================================
# 2. MODIFIERS & TRIGGERS (Данные)
# ==============================================================================


class PipelineModsDTO(BaseModel):
    """Числовые модификаторы."""

    accuracy_mult: float = 1.0
    weapon_effect_value: float = 2.0  # Универсальный бонус оружия (Crit Mult / Pierce %)


class PipelineStagesDTO(BaseModel):
    """Управление этапами."""

    check_accuracy: bool = True
    check_evasion: bool = True
    check_parry: bool = True
    check_block: bool = True
    check_crit: bool = True
    calculate_damage: bool = True
    calculate_healing: bool = False  # NEW: Этап расчета хила

    # Новый этап: Проверка контратаки
    check_counter: bool = True


# ==============================================================================
# 3. RESULT & CHAIN (Выходные данные)
# ==============================================================================


class ChainTriggersDTO(BaseModel):
    """
    Триггеры цепных реакций (Chain Reactions).
    Указывают Executor'у, что нужно создать дополнительные задачи.
    """

    trigger_offhand_attack: bool = False  # Атака второй рукой
    trigger_counter_attack: bool = False  # Контратака
    trigger_extra_strike: bool = False  # Дополнительный удар (перк)
    trigger_cleave: list[int] = Field(default_factory=list)  # IDs целей для Cleave


class CombatEventDTO(BaseModel):
    """
    Атомарное событие боя для лога.
    """

    type: Literal[
        "CAST", "HIT", "MISS", "DODGE", "PARRY", "BLOCK", "CRIT", "TICK", "DEATH", "HEAL", "COST", "APPLY_EFFECT"
    ]
    source_id: int
    target_id: int | None = None

    # Контекст (чем вызвано)
    action_id: str | None = None  # ID абилки/финта/эффекта

    # Значение (если есть)
    value: int | None = None
    resource: str | None = None  # hp, en

    # Теги (для доп. инфы)
    tags: list[str] = Field(default_factory=list)


class InteractionResultDTO(BaseModel):
    """Итоговый отчет."""

    # === Context (Кто и Кого) ===
    source_id: int | None = None
    target_id: int | None = None
    hand: str = "main"  # main, off

    # === Что случилось (Факты) ===
    is_hit: bool = False
    is_crit: bool = False
    is_blocked: bool = False
    is_parried: bool = False
    is_dodged: bool = False
    is_miss: bool = False
    is_counter: bool = False  # Старый флаг (можно оставить для совместимости или убрать)

    # === Причина пропуска ===
    skip_reason: str | None = None  # STUNNED, NO_RESOURCE, DEAD, etc.

    crit_mult: float = 1.0

    damage_raw: int = 0
    damage_mitigated: int = 0
    damage_final: int = 0
    healing_final: int = 0  # NEW: Итоговый хил
    reflected_damage: int = 0
    lifesteal_amount: int = 0  # NEW: Восстановленное HP от лайфстила

    # Токены (изменил на dict[str, int])
    tokens_awarded_attacker: dict[str, int] = Field(default_factory=dict)
    tokens_awarded_defender: dict[str, int] = Field(default_factory=dict)

    # === Events (Структурированный лог) ===
    events: list[CombatEventDTO] = Field(default_factory=list)

    # === Что надо сделать (Команды) ===
    # Список эффектов для наложения: [{"id": "bleed", "params": {"power": 30}}]
    applied_effects: list[dict[str, Any]] = Field(default_factory=list)

    # === Chain Reactions (Новые задачи) ===
    chain_events: ChainTriggersDTO = Field(default_factory=ChainTriggersDTO)

    # === Resources (Изменения ресурсов) ===
    # {"hp": {"cost": "-10", "regen": "+5"}, "en": {"cost": "-20"}}
    # Используется WaterfallCalculator для расчета итога
    resource_changes: dict[str, dict[str, str]] = Field(default_factory=dict)

    # Флаги для AbilityService (чтобы знать, какие эффекты накладывать)
    # Используется для передачи информации из Резолвера в Пост-Кальк
    ability_flags: Any = None  # TODO: Типизировать как AbilityFlagsDTO, но тут циклический импорт


# ==============================================================================
# 4. CONTEXT (Вход и Выход)
# ==============================================================================


class PipelineContextDTO(BaseModel):
    """Пульт управления боем."""

    phases: PipelinePhasesDTO = Field(default_factory=PipelinePhasesDTO)
    flags: PipelineFlagsDTO = Field(default_factory=PipelineFlagsDTO)
    mods: PipelineModsDTO = Field(default_factory=PipelineModsDTO)

    # Заменили PipelineTriggersDTO на TriggerRulesFlagsDTO
    triggers: TriggerRulesFlagsDTO = Field(default_factory=TriggerRulesFlagsDTO)

    stages: PipelineStagesDTO = Field(default_factory=PipelineStagesDTO)

    # Meta
    override_damage: tuple[float, float] | None = None

    # Calc Flags
    can_counter: bool = True

    # Result (Всегда инициализирован)
    result: InteractionResultDTO = Field(default_factory=InteractionResultDTO)

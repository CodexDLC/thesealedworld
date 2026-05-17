"""
DTO для управления Пайплайном Боя (Combat Pipeline).
Содержит флаги, контексты и результаты расчетов.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.backend.features.combat.dto.ids import ActorId, ActorIdLike, normalize_actor_id
from src.backend.features.combat.dto.trigger_rules import TriggerRulesFlagsDTO

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
    ignore_evasion_cap: bool = False
    zero_anti_evasion: bool = False

    # Parry/Block
    ignore_parry_cap: bool = False
    ignore_block_cap: bool = False

    # Crit
    crit_ignore_anticrit: bool = False
    crit_damage_boost: bool = False  # Включает повышенный урон при крите

    # Damage
    can_pierce: bool = False  # Разрешить проверку на пронзание
    ignore_armor: bool = False
    ignore_flat_armor: bool = False
    roll_flat_armor_ignore: bool = False
    boost_flat_armor_penetration: bool = False
    suppress_physical_resistance: bool = False
    ignore_physical_resistance: bool = False

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
    force_counter_on_dodge: bool = False
    force_counter_on_parry: bool = False
    counter_to_cap_on_dodge: bool = False


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
    damage_mult: float = 1.0
    weapon_effect_value: float = 2.0  # Универсальный бонус оружия (Crit Mult / Pierce %)
    weapon_technique_bonus_damage: float = 0.0
    flat_armor_penetration_bonus_pct: float = 0.0
    flat_armor_ignore_chance_bonus: float = 0.0
    physical_resistance_suppression_pct: float = 0.0


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
    preserve_feint: bool = False  # Возвратить стоимость использованного финта


class CombatEventDTO(BaseModel):
    """
    Атомарное событие боя для лога.
    """

    type: Literal[
        "CAST",
        "HIT",
        "MISS",
        "DODGE",
        "PARRY",
        "BLOCK",
        "CRIT",
        "TICK",
        "DEATH",
        "HEAL",
        "COST",
        "APPLY_EFFECT",
    ]
    source_id: ActorId
    target_id: ActorId | None = None

    # Контекст (чем вызвано)
    action_id: str | None = None  # ID абилки/финта/эффекта

    # Значение (если есть)
    value: int | None = None
    resource: str | None = None  # hp, en

    # Теги (для доп. инфы)
    tags: list[str] = Field(default_factory=list)

    @field_validator("source_id", "target_id", mode="before")
    @classmethod
    def _normalize_actor_ids(cls, value: ActorIdLike | None) -> ActorId | None:
        return normalize_actor_id(value) if value is not None else None


class CombatCheckTraceDTO(BaseModel):
    """Structured resolver check trace for one stage of one interaction."""

    stage: str
    chance: float
    roll: float | None = None
    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)


class CombatDamageTraceDTO(BaseModel):
    """Structured damage calculation trace for one interaction."""

    raw: float
    final: float
    min: float
    max: float
    details: dict[str, Any] = Field(default_factory=dict)


CombatFactOwner = Literal["source", "target", "self", "other"]
CombatTriggerSource = Literal["weapon", "feint", "style", "effect", "ability", "monster", "system"]


class CombatResourceFactDTO(BaseModel):
    """Normalized resource mutation fact produced by the combat pipeline."""

    actor_id: ActorId | None = None
    owner: CombatFactOwner = "other"
    resource: str
    reason: str
    delta: int
    before: int | None = None
    after: int | None = None
    max: int | None = None
    source_action_id: str | None = None
    source_effect_id: str | None = None
    source_trigger_id: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("actor_id", mode="before")
    @classmethod
    def _normalize_actor_id(cls, value: ActorIdLike | None) -> ActorId | None:
        return normalize_actor_id(value) if value is not None else None


class CombatTokenFactDTO(BaseModel):
    """Normalized token mutation fact produced by the combat pipeline."""

    actor_id: ActorId | None = None
    owner: CombatFactOwner = "other"
    token: str
    amount: int
    before: int | None = None
    after: int | None = None
    reason: str | None = None
    source_action_id: str | None = None
    source_effect_id: str | None = None
    source_trigger_id: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("actor_id", mode="before")
    @classmethod
    def _normalize_actor_id(cls, value: ActorIdLike | None) -> ActorId | None:
        return normalize_actor_id(value) if value is not None else None


class CombatEffectFactDTO(BaseModel):
    """Normalized effect lifecycle fact produced by the combat pipeline."""

    actor_id: ActorId | None = None
    owner: CombatFactOwner = "other"
    effect_id: str
    action: Literal["apply", "tick", "expire", "resist", "cleanse"]
    value: int | None = None
    resource: str | None = None
    duration: int | None = None
    source_action_id: str | None = None
    source_effect_id: str | None = None
    source_trigger_id: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("actor_id", mode="before")
    @classmethod
    def _normalize_actor_id(cls, value: ActorIdLike | None) -> ActorId | None:
        return normalize_actor_id(value) if value is not None else None


class CombatDeathFactDTO(BaseModel):
    """Normalized death fact produced by the combat pipeline."""

    actor_id: ActorId | None = None
    owner: CombatFactOwner = "other"
    reason: str = "death"
    source_action_id: str | None = None
    source_effect_id: str | None = None
    source_trigger_id: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("actor_id", mode="before")
    @classmethod
    def _normalize_actor_id(cls, value: ActorIdLike | None) -> ActorId | None:
        return normalize_actor_id(value) if value is not None else None


class CombatTriggerActivationDTO(BaseModel):
    """A source that enabled a trigger flag for this exchange."""

    trigger_id: str
    source: CombatTriggerSource = "system"
    source_id: str | None = None
    source_slot: str | None = None
    tags: list[str] = Field(default_factory=list)


class CombatTriggerFactDTO(BaseModel):
    """Normalized trigger fact produced when a trigger passes its chance check."""

    trigger_id: str
    event: str
    source: CombatTriggerSource = "system"
    source_id: str | None = None
    source_slot: str | None = None
    chance: float = 1.0
    display_policy: str = "merge"
    stacking_rule: str = "unique"
    tags: list[str] = Field(default_factory=list)


class CombatTriggerAttemptDTO(BaseModel):
    """A trigger chance check attempt, including failed rolls."""

    trigger_id: str
    event: str
    source: CombatTriggerSource = "system"
    source_id: str | None = None
    source_slot: str | None = None
    chance: float = 1.0
    roll: float | None = None
    passed: bool = False
    display_policy: str = "merge"
    stacking_rule: str = "unique"
    tags: list[str] = Field(default_factory=list)


class CombatPipelineMutationFactDTO(BaseModel):
    """A pipeline-local mutation applied by a feint, style, trigger, effect, or ability."""

    source: CombatTriggerSource = "system"
    source_id: str | None = None
    mutation_id: str
    path: str
    value: Any = None
    tags: list[str] = Field(default_factory=list)


class InteractionResultDTO(BaseModel):
    """Итоговый отчет."""

    # === Context (Кто и Кого) ===
    source_id: ActorId | None = None
    target_id: ActorId | None = None
    hand: str = "main"  # main, off

    @field_validator("source_id", "target_id", mode="before")
    @classmethod
    def _normalize_actor_ids(cls, value: ActorIdLike | None) -> ActorId | None:
        return normalize_actor_id(value) if value is not None else None

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

    # === Pipeline Facts (нормализованные факты для будущего public log mapping) ===
    resource_facts: list[CombatResourceFactDTO] = Field(default_factory=list)
    token_facts: list[CombatTokenFactDTO] = Field(default_factory=list)
    effect_facts: list[CombatEffectFactDTO] = Field(default_factory=list)
    death_facts: list[CombatDeathFactDTO] = Field(default_factory=list)
    trigger_facts: list[CombatTriggerFactDTO] = Field(default_factory=list)
    trigger_attempts: list[CombatTriggerAttemptDTO] = Field(default_factory=list)
    mutation_facts: list[CombatPipelineMutationFactDTO] = Field(default_factory=list)
    action_facts: dict[str, Any] = Field(default_factory=dict)

    # === Resolver Trace (для читаемого INFO лога и аналитики) ===
    checks: list[CombatCheckTraceDTO] = Field(default_factory=list)
    damage_trace: CombatDamageTraceDTO | None = None

    # === Что надо сделать (Команды) ===
    # Список эффектов для наложения: [{"id": "bleed", "params": {"power": 30}}]
    applied_effects: list[dict[str, Any]] = Field(default_factory=list)

    # === Chain Reactions (Новые задачи) ===
    chain_events: ChainTriggersDTO = Field(default_factory=ChainTriggersDTO)

    # === Fired Triggers (для log_builder) ===
    # trigger_id-значения триггеров, прошедших chance check в _resolve_triggers()
    fired_triggers: list[str] = Field(default_factory=list)

    # === Resources (Изменения ресурсов) ===
    # {"hp": {"cost": "-10", "regen": "+5"}, "en": {"cost": "-20"}}
    # Используется WaterfallCalculator для расчета итога
    resource_changes: dict[str, dict[str, str]] = Field(default_factory=dict)


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
    trigger_activations: dict[str, list[CombatTriggerActivationDTO]] = Field(default_factory=dict)

    stages: PipelineStagesDTO = Field(default_factory=PipelineStagesDTO)

    # Meta
    override_damage: tuple[float, float] | None = None

    # Calc Flags
    can_counter: bool = True

    # Result (Всегда инициализирован)
    result: InteractionResultDTO = Field(default_factory=InteractionResultDTO)

"""
Внутренние DTO для боевой системы (RBC v3.0).
Используются только внутри модуля combat.
"""

from typing import Any

from pydantic import BaseModel, Field

from src.backend.domains.user_features.combat.dto.combat_action_dto import (
    CombatActionDTO,
    CombatActionResultDTO,
    CombatMoveDTO,
)
from src.backend.resources.game_data.effects.schemas import ControlInstructionDTO
from src.shared.schemas.modifier_dto import (
    CombatModifiersDTO,
    CombatSkillsDTO,
)

# === НОВЫЕ DTO для финтов ===


class FeintCostDTO(BaseModel):
    """
    Стоимость финта в тактических токенах.
    Ключи: "hit", "crit", "block", "parry", "dodge", "tempo"
    Значения: количество токенов для списания
    """

    tactics: dict[str, int] = Field(default_factory=dict)

    def __repr__(self):
        return f"FeintCost({self.tactics})"


class FeintHandDTO(BaseModel):
    """
    Система "руки" финтов для актора.

    arsenal - весь доступный арсенал финтов актора (статичный список)
    hand - текущие финты в руке {feint_key: cost_dict}
    """

    arsenal: list[str] = Field(default_factory=list)
    hand: dict[str, dict[str, int]] = Field(default_factory=dict)

    def is_in_hand(self, feint_key: str) -> bool:
        """Проверяет есть ли финт в руке"""
        return feint_key in self.hand

    def add_to_hand(self, feint_key: str, cost: dict[str, int]) -> None:
        """Добавляет финт в руку"""
        self.hand[feint_key] = cost

    def remove_from_hand(self, feint_key: str) -> dict[str, int] | None:
        """Убирает финт из руки, возвращает его стоимость"""
        return self.hand.pop(feint_key, None)

    def get_hand_size(self) -> int:
        """Возвращает текущий размер руки"""
        return len(self.hand)

    def clear_hand(self) -> None:
        """Очищает руку (для отладки)"""
        self.hand.clear()


class ActorMetaDTO(BaseModel):
    """
    Мета-данные и Состояние (State).
    Соответствует ключу `meta` в Redis JSON.
    """

    # Identity
    id: str | int
    name: str
    type: str  # "player", "monster"
    team: str
    template_id: str | None = None
    is_ai: bool = False

    # State (Hot Data)
    hp: int = 0
    max_hp: int = 0
    en: int = 0
    max_en: int = 0
    tactics: int = 0
    is_dead: bool = False
    afk_level: int = 0
    exchange_counter: int = 0  # Счетчик участий в разменах (для кулдаунов и XP)
    tokens: dict[str, int] = Field(default_factory=dict)

    # === НОВОЕ ПОЛЕ ===
    feints: FeintHandDTO = Field(default_factory=FeintHandDTO)


class ActorRawDTO(BaseModel):
    """
    Математическая модель (Cold Data).
    Соответствует ключу `raw` в Redis JSON.
    """

    attributes: dict[str, Any] = Field(default_factory=dict)
    modifiers: dict[str, Any] = Field(default_factory=dict)


class ActorLoadoutDTO(BaseModel):
    """
    Экипировка и доступные действия.
    Соответствует ключу `loadout` в Redis JSON.
    """

    # {slot: skill_key, slot_trigger: trigger_id}
    layout: dict[str, str] = Field(default_factory=dict)
    belt: list[dict[str, Any]] = Field(default_factory=list)
    known_abilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ActiveAbilityDTO(BaseModel):
    """
    Активные способности (Стойки, Чаннелинг).
    Имеют логику (pipeline_mutations).
    """

    uid: str
    ability_id: str
    source_id: int
    expire_at_exchange: int
    impact: dict[str, int] = Field(default_factory=dict)

    # --- Memory (для отката) ---
    # Список ключей в actor.raw.modifiers, которые эта абилка изменила.
    modified_keys: list[str] = Field(default_factory=list)

    payload: dict[str, Any] = Field(default_factory=dict)


class ActiveEffectDTO(BaseModel):
    """
    Активные эффекты (Баффы, Дебаффы, Контроль).
    Влияют на статы и ресурсы.
    """

    uid: str
    effect_id: str
    source_id: int
    expire_at_exchange: int

    # --- State ---
    # Копия resource_impact из конфига (с учетом power)
    impact: dict[str, int] = Field(default_factory=dict)

    # Копия control_logic из конфига (для быстрого доступа)
    control: ControlInstructionDTO | None = None

    # Исходный множитель силы (для наследования)
    power: float = 1.0

    # Исходные параметры создания (для наследования и логики)
    params: dict[str, Any] = Field(default_factory=dict)

    # --- Memory (для отката) ---
    # Список ключей в actor.raw.modifiers, которые этот эффект изменил.
    modified_keys: list[str] = Field(default_factory=list)


class ActorStatusesDTO(BaseModel):
    """
    Контейнер для всех временных состояний.
    """

    abilities: list[ActiveAbilityDTO] = Field(default_factory=list)
    effects: list[ActiveEffectDTO] = Field(default_factory=list)


class ActorStats(BaseModel):
    """
    Готовые статы для математики (In-Memory Calculated).
    Композиция: Модификаторы (результат калькулятора) + Скиллы (из базы).
    """

    calculated_at: float = 0.0

    # 1. Результат WaterfallCalculator (Чистые цифры, включая StatusStats)
    mods: CombatModifiersDTO = Field(default_factory=CombatModifiersDTO)

    # 2. Скиллы (из Redis/Snapshot)
    skills: CombatSkillsDTO = Field(default_factory=CombatSkillsDTO)

    @classmethod
    def from_flat_dict(cls, flat_data: dict[str, Any]) -> "ActorStats":
        """
        Фабрика для создания ActorStats из плоского словаря.
        """
        mods_data = {}
        skills_data = {}

        mods_fields = CombatModifiersDTO.model_fields.keys()
        skills_fields = CombatSkillsDTO.model_fields.keys()

        for key, value in flat_data.items():
            if key in skills_fields:
                skills_data[key] = value
            elif key in mods_fields:
                mods_data[key] = value

        return cls(
            mods=CombatModifiersDTO(**mods_data),
            skills=CombatSkillsDTO(**skills_data),
        )


class ActorSnapshot(BaseModel):
    """
    Агрегатор данных актера в памяти.
    Точная копия структуры Redis JSON.
    """

    # 1. Meta & State
    meta: ActorMetaDTO

    # 2. Math Model Source
    raw: ActorRawDTO

    # 3. Skills Source
    skills: dict[str, float] = Field(default_factory=dict)

    # 4. Loadout & Config
    loadout: ActorLoadoutDTO = Field(default_factory=ActorLoadoutDTO)

    # 5. Dynamic Statuses
    statuses: ActorStatusesDTO = Field(default_factory=ActorStatusesDTO)

    xp_buffer: dict[str, int] = Field(default_factory=dict)

    # 6. Analytics & Debug
    metrics: dict[str, float] = Field(default_factory=dict)
    explanation: dict[str, str] = Field(default_factory=dict)

    # --- Calculated (In-Memory only) ---
    stats: ActorStats | None = None
    dirty_stats: set[str] = Field(default_factory=set)

    # --- Helpers ---
    @property
    def char_id(self) -> int:
        return int(self.meta.id)

    @property
    def team(self) -> str:
        return self.meta.team

    @property
    def is_alive(self) -> bool:
        return not self.meta.is_dead and self.meta.hp > 0

    @property
    def state(self) -> ActorMetaDTO:
        return self.meta

    @property
    def active_abilities(self) -> list[ActiveAbilityDTO]:
        """Helper для обратной совместимости (только абилки)."""
        return self.statuses.abilities

    @property
    def active_effects(self) -> list[ActiveEffectDTO]:
        """Helper для доступа к эффектам."""
        return self.statuses.effects


__all__ = [
    "FeintCostDTO",
    "FeintHandDTO",
    "ActorMetaDTO",
    "ActorRawDTO",
    "ActorLoadoutDTO",
    "ActiveAbilityDTO",
    "ActiveEffectDTO",
    "ActorStatusesDTO",
    "ActorStats",
    "ActorSnapshot",
    "CombatMoveDTO",
    "CombatActionDTO",
    "CombatActionResultDTO",
]

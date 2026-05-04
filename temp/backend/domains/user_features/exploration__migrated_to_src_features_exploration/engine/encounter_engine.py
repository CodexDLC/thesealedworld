# backend/domains/user_features/exploration/engine/encounter_engine.py
import random
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.domains.user_features.exploration.data.config import ExplorationConfig
from src.backend.services.calculators.chance_service import ChanceService
from src.shared.schemas.exploration import (
    DetectionStatus,
    EncounterDTO,
    EncounterOptionDTO,
    EncounterType,
    EnemyPreviewDTO,
)

if TYPE_CHECKING:
    from src.backend.domains.user_features.exploration.engine.dispatcher_bridge import (
        ExplorationDispatcherBridge,
    )


class EncounterEngine:
    """
    Движок генерации случайных встреч (V2).
    Реализует каскадную проверку событий и логику обнаружения.
    """

    def __init__(self, dispatcher_bridge: "ExplorationDispatcherBridge | None" = None):
        self._bridge = dispatcher_bridge

    async def try_generate_encounter(
        self, char_id: int, location_data: dict[str, Any], scouting_skill: int, trigger: str = "move", loc_id: str = ""
    ) -> EncounterDTO | None:
        """
        Главный метод генерации.
        """
        flags = location_data.get("flags", {})

        # 1. Safe Zone Check
        if flags.get("is_safe_zone", False):
            return None

        # 2. Rare Events Cascade
        if ChanceService.check_chance(ExplorationConfig.CHANCE_MERCHANT):
            return self._build_merchant_encounter()

        if ChanceService.check_chance(ExplorationConfig.CHANCE_QUEST):
            return self._build_quest_encounter()

        # 3. Combat Check (Trigger)
        combat_chance = ExplorationConfig.CHANCE_COMBAT_BASE
        if trigger == "search":
            combat_chance = ExplorationConfig.CHANCE_COMBAT_SEARCH

        if ChanceService.check_chance(combat_chance):
            tier = int(flags.get("threat_tier", 1))
            return await self._generate_combat(char_id, tier, scouting_skill, loc_id)

        return None

    async def _generate_combat(self, char_id: int, tier: int, scouting_skill: int, loc_id: str) -> EncounterDTO:
        """
        Генерация боевого энкаунтера.
        """
        # 1. Выбор сложности (Зависит ТОЛЬКО от Tier)
        weights_int = ExplorationConfig.TIER_DIFFICULTY_WEIGHTS.get(tier, ExplorationConfig.TIER_DIFFICULTY_WEIGHTS[1])
        # Преобразуем веса в float для ChanceService (Mypy fix)
        weights = {k: float(v) for k, v in weights_int.items()}

        difficulty = ChanceService.weighted_choice(weights)

        # 2. Detection Check (Scouting vs Difficulty)
        # Скилл игрока влияет на то, заметит ли он врага (DETECTED) или попадет в засаду (AMBUSH)

        # Сложность обнаружения зависит от сложности моба
        diff_mod = ExplorationConfig.DETECTION_MODIFIERS.get(difficulty, 0)
        loc_difficulty = (tier * 10) + diff_mod

        # Formula: Diff = Scouting - Difficulty + Random(-5, 5)
        diff = scouting_skill - loc_difficulty + ChanceService.random_range(-5, 5)

        status = DetectionStatus.DETECTED if diff >= 0 else DetectionStatus.AMBUSH

        # 3. Сборка мобов
        enemies = self._mock_enemies(tier, difficulty)

        # 4. Создание боевой сессии через Bridge
        session_id = None
        if self._bridge:
            try:
                session_id = await self._bridge.create_combat_session(
                    char_id=char_id,
                    enemies=[e.model_dump() for e in enemies],
                    loc_id=loc_id,
                    ambush=(status == DetectionStatus.AMBUSH),
                )
                log.info(f"EncounterEngine | combat_session_created char_id={char_id} session_id={session_id}")
            except Exception as e:  # noqa: BLE001
                log.error(f"EncounterEngine | combat_session_error char_id={char_id} error={e}")

        # 5. Сборка DTO
        return self._build_combat_dto(status, enemies, tier, session_id)

    def _mock_enemies(self, tier: int, difficulty: str) -> list[EnemyPreviewDTO]:
        """
        Временная заглушка для генерации врагов.
        """
        base_lvl = tier * 5
        if difficulty == "hard":
            return [EnemyPreviewDTO(name=f"Alpha Wolf (T{tier})", level=base_lvl + 2, hp_percent=100)]
        elif difficulty == "mid":
            return [EnemyPreviewDTO(name=f"Wolf Pack (T{tier})", level=base_lvl, hp_percent=100)]
        else:
            return [EnemyPreviewDTO(name=f"Rat (T{tier})", level=base_lvl - 1, hp_percent=100)]

    def _build_combat_dto(
        self, status: DetectionStatus, enemies: list[EnemyPreviewDTO], tier: int, session_id: str | None = None
    ) -> EncounterDTO:
        enemy_name = enemies[0].name if enemies else "Unknown Threat"

        if status == DetectionStatus.DETECTED:
            title = "👁 УГРОЗА ОБНАРУЖЕНА"
            desc = f"Вы замечаете: {enemy_name}. Они вас еще не видели."
            options = [
                EncounterOptionDTO(id="attack", label="⚔️ Атаковать", style="danger"),
                EncounterOptionDTO(id="bypass", label="👣 Обойти", style="secondary"),
                EncounterOptionDTO(id="inspect", label="🔍 Изучить", style="primary"),
            ]
        else:
            title = "⚔️ ЗАСАДА!"
            desc = f"{enemy_name} нападает из засады! Вы не успели среагировать."
            options = [
                EncounterOptionDTO(id="attack", label="🛡 В бой!", style="danger"),
            ]

        return EncounterDTO(
            id=f"combat_{random.randint(1000, 9999)}",
            type=EncounterType.COMBAT,
            status=status,
            title=title,
            description=desc,
            enemies=enemies,
            options=options,
            session_id=session_id,
            metadata={"tier": tier},
        )

    def _build_merchant_encounter(self) -> EncounterDTO:
        return EncounterDTO(
            id="merchant_01",
            type=EncounterType.MERCHANT,
            title="💰 Странствующий Торговец",
            description="Вы встречаете торговца с повозкой.",
            options=[
                EncounterOptionDTO(id="trade", label="🤝 Торговать", style="primary"),
                EncounterOptionDTO(id="bypass", label="👋 Уйти", style="secondary"),
            ],
        )

    def _build_quest_encounter(self) -> EncounterDTO:
        return EncounterDTO(
            id="quest_01",
            type=EncounterType.QUEST,
            title="📜 Странник",
            description="Человек у дороги просит помощи.",
            options=[
                EncounterOptionDTO(id="talk", label="🗣 Говорить", style="primary"),
                EncounterOptionDTO(id="bypass", label="👋 Уйти", style="secondary"),
            ],
        )

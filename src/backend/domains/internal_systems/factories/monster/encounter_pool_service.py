# apps/game_core/modules/monster/encounter_pool_service.py
import random
from typing import TYPE_CHECKING
from uuid import UUID

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.postgres.models import GeneratedClanORM
from src.backend.database.postgres.repositories import MonsterRepository
from src.backend.domains.internal_systems.factories.monster.clan_hashing import compute_context_hash, normalize_tags
from src.shared.schemas.monster_dto import GeneratedMonsterDTO

if TYPE_CHECKING:
    from src.backend.domains.user_features.exploration.services.exploration_service import (
        ExplorationService as GameWorldService,
    )


class EncounterPoolService:
    """
    Сервис для выбора случайной встречи из пула уже сгенерированных кланов.
    Может использовать GameWorldService для получения контекста локации.
    """

    def __init__(self, session: AsyncSession, game_world_service: "GameWorldService | None" = None):
        self.session = session
        self.repo = MonsterRepository(session)
        self.game_world_service = game_world_service

    # --- Legacy (пока оставим, если где-то используется) ---
    async def get_random_encounter(self, tier: int, biome_id: str, raw_tags: list[str]) -> GeneratedClanORM | None:
        normalized_tags = normalize_tags(raw_tags)
        context_hash = compute_context_hash(tier, biome_id, normalized_tags)
        candidate_clans = await self.repo.get_clans_by_context_hash(context_hash)
        if not candidate_clans:
            return None
        return random.choice(candidate_clans)

    # --- New API ---

    async def get_random_clan_id(self, tier: int, biome_id: str, raw_tags: list[str]) -> UUID | None:
        """
        Возвращает ID случайного клана, подходящего под условия.
        """
        normalized_tags = normalize_tags(raw_tags)
        context_hash = compute_context_hash(tier, biome_id, normalized_tags)

        clan_ids = await self.repo.get_clan_ids_by_context_hash(context_hash)

        if not clan_ids:
            log.warning(f"EncounterPool | No clans found for hash='{context_hash}'")
            return None

        return random.choice(clan_ids)

    async def get_clan_members_dto(self, clan_id: UUID) -> list[GeneratedMonsterDTO]:
        """
        Возвращает список DTO всех монстров клана.
        """
        monsters_orm = await self.repo.get_clan_members(clan_id)
        return [GeneratedMonsterDTO.model_validate(m) for m in monsters_orm]

    async def get_random_monster_dto(
        self,
        tier: int,
        biome_id: str,
        raw_tags: list[str],
        role_filter: str | None = None,
        exclude_role: str | None = None,
    ) -> GeneratedMonsterDTO | None:
        """
        Умный метод: находит клан, берет всех монстров, фильтрует и возвращает одного случайного.
        """
        # 1. Находим клан
        clan_id = await self.get_random_clan_id(tier, biome_id, raw_tags)
        if not clan_id:
            return None

        # 2. Получаем всех монстров клана
        members = await self.get_clan_members_dto(clan_id)
        if not members:
            log.warning(f"EncounterPool | Clan {clan_id} has no members!")
            return None

        # 3. Фильтрация
        candidates = members

        if role_filter:
            candidates = [m for m in candidates if m.role == role_filter]

        if exclude_role:
            candidates = [m for m in candidates if m.role != exclude_role]

        if not candidates:
            log.warning(
                f"EncounterPool | No monsters left after filtering (role={role_filter}, exclude={exclude_role})"
            )
            return None

        # 4. Выбор
        selected = random.choice(candidates)
        log.info(f"EncounterPool | Selected monster: {selected.name} ({selected.role}) from clan {clan_id}")

        return selected

    async def get_tutorial_encounter(self, loc_id: str) -> GeneratedMonsterDTO | None:
        """
        Специальный метод для туториала.
        Сам получает параметры локации и ищет миньона.
        """
        if not self.game_world_service:
            raise RuntimeError("GameWorldService is required for get_tutorial_encounter")

        # 1. Получаем параметры локации
        params = await self.game_world_service.get_location_encounter_params(loc_id)
        if not params:
            log.error(f"EncounterPool | Failed to get location params for {loc_id}")
            # Fallback params?
            params = {"tier": 1, "biome": "wasteland", "tags": ["ruins"]}

        # 2. Ищем миньона
        return await self.get_random_monster_dto(
            tier=params["tier"], biome_id=params["biome"], raw_tags=params["tags"], role_filter="minion"
        )

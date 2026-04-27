# apps/shared/database/db_contract/i_monster_repository.py
from abc import ABC, abstractmethod
from uuid import UUID

from src.backend.database.postgres.models import GeneratedClanORM, GeneratedMonsterORM


class IMonsterRepository(ABC):
    @abstractmethod
    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClanORM | None:
        pass

    @abstractmethod
    async def create_clan_with_members(
        self, clan_orm: GeneratedClanORM, monsters_orm: list[GeneratedMonsterORM]
    ) -> GeneratedClanORM:
        pass

    @abstractmethod
    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClanORM]:
        """
        Ищет ВСЕ кланы, доступные в данном контексте (Tier + Biome + Tags).
        """
        pass

    @abstractmethod
    async def get_monster_by_id(self, monster_id: UUID | str) -> GeneratedMonsterORM | None:
        pass

    @abstractmethod
    async def get_monsters_batch(self, monster_ids: list[str]) -> list[GeneratedMonsterORM]:
        """
        Возвращает список монстров по списку ID.
        """
        pass

    @abstractmethod
    async def get_all_clans(self) -> list[GeneratedClanORM]:
        pass

    @abstractmethod
    async def get_clans_by_zone(self, zone_id: str) -> list[GeneratedClanORM]:
        pass

    @abstractmethod
    async def get_monsters_by_role_and_threat(
        self, role: str, min_threat: int, max_threat: int, limit: int = 5
    ) -> list[GeneratedMonsterORM]:
        pass

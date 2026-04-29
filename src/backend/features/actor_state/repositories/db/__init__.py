from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.actor_state.repositories.db.character_repository import (
    CharacterAttributesRepoORM,
    CharacterAttributesRepository,
    CharacterRepository,
    CharactersRepoORM,
)
from src.backend.features.actor_state.repositories.db.inventory_repository import InventoryRepo, InventoryRepository
from src.backend.features.actor_state.repositories.db.monster_repository import MonsterRepository
from src.backend.features.actor_state.repositories.db.skill_repository import SkillProgressRepo, SkillProgressRepository
from src.backend.features.actor_state.repositories.db.symbiote_repository import SymbioteRepoORM, SymbioteRepository
from src.backend.features.actor_state.repositories.db.wallet_repository import WalletRepoORM, WalletRepository

__all__ = [
    "CharacterRepository",
    "CharacterAttributesRepository",
    "CharactersRepoORM",
    "CharacterAttributesRepoORM",
    "InventoryRepository",
    "InventoryRepo",
    "SkillProgressRepository",
    "SkillProgressRepo",
    "SymbioteRepository",
    "SymbioteRepoORM",
    "MonsterRepository",
    "WalletRepository",
    "WalletRepoORM",
    "get_character_repo",
    "get_character_attributes_repo",
    "get_character_stats_repo",
    "get_inventory_repo",
    "get_skill_progress_repo",
    "get_symbiote_repo",
    "get_monster_repo",
    "get_wallet_repo",
]


def get_character_repo(session: AsyncSession) -> CharacterRepository:
    return CharacterRepository(session=session)


def get_character_attributes_repo(session: AsyncSession) -> CharacterAttributesRepository:
    return CharacterAttributesRepository(session=session)


get_character_stats_repo = get_character_attributes_repo


def get_inventory_repo(session: AsyncSession) -> InventoryRepository:
    return InventoryRepository(session=session)


def get_skill_progress_repo(session: AsyncSession) -> SkillProgressRepository:
    return SkillProgressRepository(session=session)


def get_symbiote_repo(session: AsyncSession) -> SymbioteRepository:
    return SymbioteRepository(session=session)


def get_monster_repo(session: AsyncSession) -> MonsterRepository:
    return MonsterRepository(session=session)


def get_wallet_repo(session: AsyncSession) -> WalletRepository:
    return WalletRepository(session=session)

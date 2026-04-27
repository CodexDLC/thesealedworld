# database/repositories/__init__.py

# 1. Мы импортируем AsyncSession из SQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.db_contract.i_characters_repo import (
    ICharacterAttributesRepo,
    ICharactersRepo,
    ICharacterStatsRepo,
)
from src.backend.database.db_contract.i_inventory_repo import IInventoryRepo
from src.backend.database.db_contract.i_leaderboard_repo import ILeaderboardRepo
from src.backend.database.db_contract.i_monster_repository import IMonsterRepository
from src.backend.database.db_contract.i_skill_repo import ISkillProgressRepo
from src.backend.database.db_contract.i_symbiote_repo import ISymbioteRepo
from src.backend.database.db_contract.i_users_repo import IUserRepo
from src.backend.database.db_contract.i_wallet_repo import IWalletRepo
from src.backend.database.db_contract.i_world_repo import IWorldRepo
from src.backend.database.postgres.repositories.characters_repo_orm import (
    CharacterAttributesRepoORM,
    CharactersRepoORM,
)
from src.backend.database.postgres.repositories.inventory_repo import InventoryRepo
from src.backend.database.postgres.repositories.leaderboard_repo import LeaderboardRepoORM
from src.backend.database.postgres.repositories.monster_repository import MonsterRepository
from src.backend.database.postgres.repositories.skill_repo import SkillProgressRepo
from src.backend.database.postgres.repositories.symbiote_repo import SymbioteRepoORM
from src.backend.database.postgres.repositories.users_repo_orm import UsersRepoORM
from src.backend.database.postgres.repositories.wallet_repo import WalletRepoORM
from src.backend.database.postgres.repositories.world_repo import WorldRepoORM

# Explicit export to satisfy linter (F401)
__all__ = [
    "ICharacterStatsRepo",
    "ICharacterAttributesRepo",
    "ICharactersRepo",
    "IInventoryRepo",
    "ILeaderboardRepo",
    "IMonsterRepository",
    "ISkillProgressRepo",
    "ISymbioteRepo",
    "IWalletRepo",
    "IWorldRepo",
    "CharacterAttributesRepoORM",
    "CharactersRepoORM",
    "LeaderboardRepoORM",
    "SkillProgressRepo",
    "SymbioteRepoORM",
    "UsersRepoORM",
    "WalletRepoORM",
    "InventoryRepo",  # Added
    "WorldRepoORM",  # Added
    "get_user_repo",
    "get_character_repo",
    "get_character_attributes_repo",
    "get_character_stats_repo",
    "get_skill_progress_repo",
    "get_inventory_repo",
    "get_symbiote_repo",
    "get_wallet_repo",
    "get_leaderboard_repo",
    "get_world_repo",
    "get_monster_repo",
]


def get_user_repo(session: AsyncSession) -> IUserRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ место, которое знает,
    какую реализацию IUserRepo мы используем.
    """
    # Сейчас мы возвращаем ORM-реализацию
    return UsersRepoORM(session=session)


def get_character_repo(session: AsyncSession) -> ICharactersRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ место, которое знает,
    какую реализацию ICharacterRepo мы используем.
    """
    return CharactersRepoORM(session=session)


def get_character_attributes_repo(session: AsyncSession) -> ICharacterAttributesRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ
    место, которое знает,
    какую реализацию ICharacterAttributes мы используем.
    """
    return CharacterAttributesRepoORM(session)


# Alias for backward compatibility
get_character_stats_repo = get_character_attributes_repo


def get_skill_progress_repo(session: AsyncSession) -> ISkillProgressRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ
    место, которое знает,
    какую реализацию ISkillProgressRepo мы используем.
    """
    return SkillProgressRepo(session)


def get_inventory_repo(session: AsyncSession) -> IInventoryRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ
    место, которое знает,
    какую реализацию IInventoryRepo
    мы используем.
    """

    return InventoryRepo(session=session)


def get_symbiote_repo(session: AsyncSession) -> ISymbioteRepo:
    """
    Возвращает репозиторий для работы с Симбиотом.
    """
    return SymbioteRepoORM(session=session)


def get_wallet_repo(session: AsyncSession) -> IWalletRepo:
    """
    Возвращает репозиторий для работы с Кошельком.
    """
    return WalletRepoORM(session=session)


def get_leaderboard_repo(session: AsyncSession) -> ILeaderboardRepo:
    """
    Возвращает репозиторий для работы с Лидербордом.
    """

    return LeaderboardRepoORM(session=session)


def get_world_repo(session: AsyncSession) -> IWorldRepo:
    """
    Возвращает репозиторий для работы с Миром.
    """
    return WorldRepoORM(session=session)


def get_monster_repo(session: AsyncSession) -> IMonsterRepository:
    """
    Единственное место, которое знает, какую реализацию IMonsterRepository мы используем.
    """
    return MonsterRepository(session=session)

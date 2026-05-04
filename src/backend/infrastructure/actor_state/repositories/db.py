from sqlalchemy.ext.asyncio import AsyncSession

from .attributes import CharacterAttributesRepository
from .character import CharacterRepository
from .inventory import InventoryRepository, WalletRepository
from .monster import MonsterRepository
from .skill import SkillRepository
from .symbiote import SymbioteRepository


def get_char_repo(session: AsyncSession) -> CharacterRepository:
    return CharacterRepository(session)


def get_character_repo(session: AsyncSession) -> CharacterRepository:
    return CharacterRepository(session)


def get_attributes_repo(session: AsyncSession) -> CharacterAttributesRepository:
    return CharacterAttributesRepository(session)


def get_character_attributes_repo(session: AsyncSession) -> CharacterAttributesRepository:
    return CharacterAttributesRepository(session)


def get_inventory_repo(session: AsyncSession) -> InventoryRepository:
    return InventoryRepository(session)


def get_wallet_repo(session: AsyncSession) -> WalletRepository:
    return WalletRepository(session)


def get_skill_repo(session: AsyncSession) -> SkillRepository:
    return SkillRepository(session)


def get_skill_progress_repo(session: AsyncSession) -> SkillRepository:
    return SkillRepository(session)


def get_symbiote_repo(session: AsyncSession) -> SymbioteRepository:
    return SymbioteRepository(session)


def get_monster_repo(session: AsyncSession) -> MonsterRepository:
    return MonsterRepository(session)

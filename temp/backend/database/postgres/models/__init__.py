# backend/database/postgres/models/__init__.py
from .base import Base
from .character import Character, CharacterAttributes
from .inventory import InventoryItem, ResourceWallet
from .leaderboard import Leaderboard
from .monster import GeneratedClanORM, GeneratedMonsterORM
from .scenario import CharacterScenarioState, ScenarioMaster, ScenarioNode
from .skill import CharacterSkillProgress
from .symbiote import CharacterSymbiote
from .user import User
from .world import WorldGrid, WorldRegion, WorldZone

# Экспортируем Base и все модели для Alembic
# Важно: Alembic должен импортировать этот файл, чтобы увидеть все модели в Base.metadata
__all__ = [
    "Base",
    "User",
    "Character",
    "CharacterAttributes",
    "InventoryItem",
    "ResourceWallet",
    "CharacterSkillProgress",
    "WorldRegion",
    "WorldZone",
    "WorldGrid",
    "GeneratedClanORM",
    "GeneratedMonsterORM",
    "ScenarioMaster",
    "ScenarioNode",
    "CharacterScenarioState",
    "CharacterSymbiote",
    "Leaderboard",
]

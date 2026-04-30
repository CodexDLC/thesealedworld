"""
Import all ORM models so Alembic sees the complete Base.metadata.
Only ORM models are allowed here.
"""

from src.backend.features.auth.models.refresh_token import RefreshToken
from src.backend.features.auth.models.user import User
from src.backend.infrastructure.db.actor_state.models import (
    Character,
    CharacterAttributes,
    CharacterSymbiote,
    GeneratedClanORM,
    GeneratedMonsterORM,
    InventoryItem,
    ResourceWallet,
    SkillProgress,
)
from src.backend.infrastructure.db.scenario.models import CharacterQuestState, ScenarioMaster, ScenarioNode
from src.backend.infrastructure.db.world.models import WorldGrid, WorldRegion, WorldZone

__all__ = [
    "User",
    "RefreshToken",
    "Character",
    "CharacterAttributes",
    "InventoryItem",
    "ResourceWallet",
    "SkillProgress",
    "CharacterSymbiote",
    "GeneratedClanORM",
    "GeneratedMonsterORM",
    "ScenarioMaster",
    "ScenarioNode",
    "CharacterQuestState",
    "WorldRegion",
    "WorldZone",
    "WorldGrid",
]

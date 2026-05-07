"""
Import all ORM models so Alembic sees the complete Base.metadata.
Only ORM models are allowed here.
"""

from src.backend.features.character.models import Character, CharacterAttributes, CharacterSymbiote, SkillProgress
from src.backend.features.items.models import (
    ItemInstance,
    ItemOrigin,
    ItemPlacement,
    ItemTransaction,
    ResourceBalance,
    ResourceTransaction,
)
from src.backend.features_site.auth.models.refresh_token import RefreshToken
from src.backend.features_site.auth.models.user import User
from src.backend.infrastructure.arena.models import (
    ArenaBrawlXP,
    ArenaLeague,
    ArenaMatch,
    ArenaRating,
    ArenaSeason,
    ArenaSeasonReward,
    ArenaTeam,
    ArenaTeamMembership,
)
from src.backend.infrastructure.inventory import InventoryItem, ResourceWallet
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM
from src.backend.infrastructure.scenario.models import CharacterQuestState, ScenarioMaster, ScenarioNode
from src.backend.infrastructure.world.models import WorldGrid, WorldRegion, WorldZone

__all__ = [
    "User",
    "RefreshToken",
    "ItemInstance",
    "ItemOrigin",
    "ItemPlacement",
    "ItemTransaction",
    "ResourceBalance",
    "ResourceTransaction",
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
    "ArenaBrawlXP",
    "ArenaLeague",
    "ArenaMatch",
    "ArenaRating",
    "ArenaSeason",
    "ArenaSeasonReward",
    "ArenaTeam",
    "ArenaTeamMembership",
]

"""
Import all ORM models so Alembic sees the complete Base.metadata.
Only ORM models are allowed here.
"""

from src.backend.chat.models.message import ChatMessage
from src.backend.chat.models.session import ChatSession, ChatSessionMessage
from src.backend.features.character.models import (
    Character,
    CharacterAttributes,
    CharacterProgression,
    CharacterSymbiote,
    SkillProgress,
)
from src.backend.features.city_services.models import CharacterTavernRoom
from src.backend.features.expedition.models import CharacterExpedition
from src.backend.features.exploration.models import CharacterLocationKnowledge
from src.backend.features.generation_ai.models import AIGenerationTask
from src.backend.features.items.models import (
    ItemGeneratedTemplate,
    ItemInstance,
    ItemOrigin,
    ItemPlacement,
    ItemTransaction,
    ResourceBalance,
    ResourceTransaction,
)
from src.backend.features.npc.models import CharacterNpcEffectLog, CharacterNpcState
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
from src.backend.infrastructure.combat.models import CombatBalanceRollup, CombatExchangeFact, CombatFinalization
from src.backend.infrastructure.inventory import InventoryItem, ResourceWallet
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM
from src.backend.infrastructure.scenario.models import CharacterQuestState, ScenarioMaster, ScenarioNode
from src.backend.infrastructure.world.models import WorldGrid, WorldRegion, WorldZone

__all__ = [
    "ChatMessage",
    "ChatSession",
    "ChatSessionMessage",
    "ItemInstance",
    "ItemGeneratedTemplate",
    "ItemOrigin",
    "ItemPlacement",
    "ItemTransaction",
    "ResourceBalance",
    "ResourceTransaction",
    "CharacterNpcEffectLog",
    "CharacterNpcState",
    "Character",
    "CharacterAttributes",
    "CharacterProgression",
    "CharacterExpedition",
    "CharacterLocationKnowledge",
    "AIGenerationTask",
    "InventoryItem",
    "ResourceWallet",
    "SkillProgress",
    "CharacterSymbiote",
    "CharacterTavernRoom",
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
    "CombatFinalization",
    "CombatExchangeFact",
    "CombatBalanceRollup",
]

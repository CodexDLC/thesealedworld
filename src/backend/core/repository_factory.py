from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.character.repositories import (
    CharacterAttributesRepository,
    CharacterProgressionRepository,
    CharacterRepository,
    SkillRepository,
    SymbioteRepository,
)
from src.backend.features.expedition import CharacterExpeditionRepository
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.infrastructure.inventory import InventoryRepository, WalletRepository
from src.backend.infrastructure.monsters import MonsterRepository
from src.backend.infrastructure.scenario.repositories import ScenarioRepository
from src.backend.infrastructure.world.repositories import WorldRepository


@dataclass(frozen=True)
class ActorStateRepositories:
    characters: CharacterRepository
    attributes: CharacterAttributesRepository
    monsters: MonsterRepository
    inventory: InventoryRepository
    wallet: WalletRepository
    skills: SkillRepository
    progression: CharacterProgressionRepository
    symbiote: SymbioteRepository
    expeditions: CharacterExpeditionRepository


@dataclass(frozen=True)
class ContentRepositories:
    scenario: ScenarioRepository
    world: WorldRepository
    items: ItemInstanceRepository
    monsters: MonsterGenerationRepository


class RepositoryFactory:
    def actor_state(self, session: AsyncSession) -> ActorStateRepositories:
        return ActorStateRepositories(
            characters=CharacterRepository(session),
            attributes=CharacterAttributesRepository(session),
            monsters=MonsterRepository(session),
            inventory=InventoryRepository(session),
            wallet=WalletRepository(session),
            skills=SkillRepository(session),
            progression=CharacterProgressionRepository(session),
            symbiote=SymbioteRepository(session),
            expeditions=CharacterExpeditionRepository(session),
        )

    def content(self, session: AsyncSession) -> ContentRepositories:
        return ContentRepositories(
            scenario=ScenarioRepository(session),
            world=WorldRepository(session),
            items=ItemInstanceRepository(session),
            monsters=MonsterGenerationRepository(session),
        )

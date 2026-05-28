from __future__ import annotations

from fastapi import Depends

from src.backend.core.database import get_db
from src.backend.features.admin_players.generation_service import AdminPlayerCharacterGenerationService
from src.backend.features.admin_players.repositories import AdminPlayerReadRepository
from src.backend.features.admin_players.services import AdminPlayerReadService
from src.backend.features.character.repositories import (
    CharacterAttributesRepository,
    CharacterProgressionRepository,
    CharacterRepository,
    SkillRepository,
)
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.items.services.generation_service import ItemGenerationService
from src.backend.features.monsters.repositories import MonsterGenerationRepository


def get_admin_player_read_service(db_session=Depends(get_db)) -> AdminPlayerReadService:
    return AdminPlayerReadService(AdminPlayerReadRepository(db_session))


def get_admin_player_generation_service(db_session=Depends(get_db)) -> AdminPlayerCharacterGenerationService:
    item_persistence = ItemPersistenceIntegration(ItemInstanceRepository(db_session))
    return AdminPlayerCharacterGenerationService(
        character_repo=CharacterRepository(db_session),
        attributes_repo=CharacterAttributesRepository(db_session),
        skill_repo=SkillRepository(db_session),
        progression_repo=CharacterProgressionRepository(db_session),
        item_generation=ItemGenerationService(persistence=item_persistence),
        monster_repo=MonsterGenerationRepository(db_session),
    )

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from src.backend.infrastructure.actor_state.repositories import (
    MonsterRepository,
    SkillRepository,
    SymbioteRepository,
    WalletRepository,
)
from sqlalchemy.exc import SQLAlchemyError

@pytest.mark.unit
class TestOtherActorStateRepositories:
    @pytest.fixture
    def session(self):
        return MagicMock()

    async def test_monster_repo(self, session):
        repo = MonsterRepository(session)
        uid = str(uuid.uuid4())
        mock_result = MagicMock()
        mock_result.all.return_value = [{"id": uid}]
        session.scalars = AsyncMock(return_value=mock_result)

        result = await repo.get_monsters_batch([uid])
        assert len(result) == 1

        # Test invalid UUID
        assert await repo.get_monsters_batch(["invalid"]) == []

        session.scalars = AsyncMock(side_effect=SQLAlchemyError())
        with pytest.raises(SQLAlchemyError):
            await repo.get_monsters_batch([uid])

    async def test_skill_repo(self, session, mocker):
        repo = SkillRepository(session)
        mock_skill = MagicMock(character_id=1)
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_skill]
        session.scalars = AsyncMock(return_value=mock_result)

        mocker.patch("src.shared.schemas.skill.SkillProgressDTO.model_validate", lambda x: x)

        result = await repo.get_all_skills_progress_batch([1])
        assert 1 in result
        assert await repo.get_all_skills_progress_batch([]) == {}

    async def test_symbiote_repo(self, session):
        repo = SymbioteRepository(session)
        mock_sym = MagicMock(character_id=1)
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_sym]
        session.scalars = AsyncMock(return_value=mock_result)

        result = await repo.get_symbiotes_batch([1])
        assert len(result) == 1
        assert await repo.get_symbiotes_batch([]) == []

    async def test_wallet_repo(self, session):
        repo = WalletRepository(session)
        mock_wallet = MagicMock(character_id=1)
        session.scalar = AsyncMock(return_value=mock_wallet)

        result = await repo.get_wallet(1)
        assert result.character_id == 1

        session.scalar = AsyncMock(side_effect=SQLAlchemyError())
        with pytest.raises(SQLAlchemyError):
            await repo.get_wallet(1)

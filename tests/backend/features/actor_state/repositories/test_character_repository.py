import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.infrastructure.actor_state.repositories import CharacterRepository, CharacterAttributesRepository
from src.shared.schemas.character import CharacterReadDTO, CharacterAttributesReadDTO
from sqlalchemy.exc import SQLAlchemyError

@pytest.mark.unit
class TestCharacterRepositories:
    @pytest.fixture
    def session(self):
        return MagicMock()

    async def test_get_characters_batch(self, session):
        repo = CharacterRepository(session)
        mock_char = MagicMock()
        mock_char.character_id = 1
        # mock_char.model_dump would be used by model_validate if it's from_attributes=True
        # but CharacterReadDTO likely expects attributes or a dict

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_char]
        session.scalars = AsyncMock(return_value=mock_result)

        # We need to mock model_validate to avoid actual Pydantic validation if it's too complex
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(CharacterReadDTO, "model_validate", lambda x: x)
            result = await repo.get_characters_batch([1])
            assert len(result) == 1
            assert result[0].character_id == 1

    async def test_get_characters_batch_empty(self, session):
        repo = CharacterRepository(session)
        assert await repo.get_characters_batch([]) == []

    async def test_get_characters_batch_error(self, session):
        repo = CharacterRepository(session)
        session.scalars = AsyncMock(side_effect=SQLAlchemyError("db fail"))
        with pytest.raises(SQLAlchemyError):
            await repo.get_characters_batch([1])

    async def test_get_attributes_batch(self, session):
        repo = CharacterAttributesRepository(session)
        mock_attr = MagicMock()
        mock_attr.character_id = 1

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_attr]
        session.scalars = AsyncMock(return_value=mock_result)

    async def test_get_attributes_batch_empty(self, session):
        repo = CharacterAttributesRepository(session)
        assert await repo.get_attributes_batch([]) == []

    async def test_get_attributes_batch_error(self, session):
        repo = CharacterAttributesRepository(session)
        session.scalars = AsyncMock(side_effect=SQLAlchemyError("db fail"))
        with pytest.raises(SQLAlchemyError):
            await repo.get_attributes_batch([1])

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from src.backend.features.auth.repositories.user_repository import UserRepository
from src.backend.features.auth.repositories.token_repository import TokenRepository
from src.backend.features.auth.models import User, RefreshToken
from src.backend.features.auth.dto.user import UserCreate

@pytest.mark.unit
class TestUserRepository:
    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return UserRepository(session)

    async def test_get_by_id(self, repo, session):
        user_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "user"
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(user_id)
        assert result == "user"
        session.execute.assert_called_once()

    async def test_get_by_email(self, repo, session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "user"
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_email("test@e.com")
        assert result == "user"
        session.execute.assert_called_once()

    async def test_create_user(self, repo, session):
        user_in = UserCreate(email="test@e.com", password="password123")

        result = await repo.create(user_in)
        assert result.email == "test@e.com"
        session.add.assert_called_once()
        session.flush.assert_called_once()
        session.refresh.assert_called_once()

    async def test_commit(self, repo, session):
        await repo.commit()
        session.commit.assert_called_once()

@pytest.mark.unit
class TestTokenRepository:
    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return TokenRepository(session)

    async def test_get_by_token(self, repo, session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "token"
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_token("token_str")
        assert result == "token"
        session.execute.assert_called_once()

    async def test_create_token(self, repo, session):
        from datetime import datetime
        user_id = uuid.uuid4()
        expires = datetime.now()

        result = await repo.create(user_id, "token_str", expires)
        assert result.user_id == user_id
        assert result.token == "token_str"
        session.add.assert_called_once()
        session.flush.assert_called_once()

    async def test_delete_token(self, repo, session):
        await repo.delete("token_str")
        session.execute.assert_called_once()

    async def test_delete_all_for_user(self, repo, session):
        await repo.delete_all_for_user(uuid.uuid4())
        session.execute.assert_called_once()

    async def test_commit(self, repo, session):
        await repo.commit()
        session.commit.assert_called_once()

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.core.database.session import get_db, get_session_context

@pytest.mark.unit
class TestDatabaseSession:
    @pytest.mark.asyncio
    async def test_get_db_yields_session(self, mocker):
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        mocker.patch("src.backend.core.database.session.async_session_factory", return_value=mock_ctx)

        async for session in get_db():
            assert session == mock_session

        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_session_context_commits_on_success(self, mocker):
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        mocker.patch("src.backend.core.database.session.async_session_factory", return_value=mock_ctx)

        async with get_session_context() as session:
            assert session == mock_session

        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_session_context_rolls_back_on_error(self, mocker):
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        mocker.patch("src.backend.core.database.session.async_session_factory", return_value=mock_ctx)

        with pytest.raises(RuntimeError, match="test error"):
            async with get_session_context() as session:
                raise RuntimeError("test error")

        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_session_context_sqlalchemy_error(self, mocker):
        from sqlalchemy.exc import SQLAlchemyError
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mocker.patch("src.backend.core.database.session.async_session_factory", return_value=mock_ctx)

        with pytest.raises(SQLAlchemyError):
            async with get_session_context() as session:
                raise SQLAlchemyError("db error")

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_db_rollback_on_error(self, mocker):
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mocker.patch("src.backend.core.database.session.async_session_factory", return_value=mock_ctx)

        gen = get_db()
        # Start the generator
        await gen.__anext__()

        with pytest.raises(RuntimeError, match="test error"):
            await gen.athrow(RuntimeError("test error"))

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_db_tables(self, mocker):
        from src.backend.core.database.session import create_db_tables
        mock_conn = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.begin = MagicMock(return_value=mock_conn)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        mocker.patch("src.backend.core.database.session.async_engine", mock_engine)

        await create_db_tables()

        mock_conn.run_sync.assert_called_once()

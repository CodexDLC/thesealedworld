import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.backend.features.actor_state.services.actor_state_service import ActorStateService
from src.backend.features.actor_state.dto.snapshot import ActorSnapshotBatchResult

@pytest.mark.unit
class TestActorStateService:
    @pytest.fixture
    def snapshot_manager(self):
        return MagicMock()

    @pytest.fixture
    def redis(self):
        return MagicMock()

    @pytest.fixture
    def session_factory(self):
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value="session")
        mock_ctx.__aexit__ = AsyncMock()
        return MagicMock(return_value=mock_ctx)

    @pytest.fixture
    def service(self, snapshot_manager, redis, session_factory):
        return ActorStateService(snapshot_manager, redis, session_factory)

    async def test_prepare_snapshots_success(self, service, snapshot_manager, mocker):
        # Mock assemblers
        m_player = mocker.patch("src.backend.features.actor_state.runtime.assemblers.player_assembler.build_snapshots",
                               AsyncMock(return_value={1: {"meta": {}}}))
        m_monster = mocker.patch("src.backend.features.actor_state.runtime.assemblers.monster_assembler.build_snapshots",
                                AsyncMock(return_value={"m1": {"meta": {}}}))

        snapshot_manager.save_snapshots = AsyncMock(return_value={
            "s1:player:1": "key1",
            "s1:monster:m1": "key2"
        })

        result = await service.prepare_snapshots("s1", [1], ["m1"])

        assert isinstance(result, ActorSnapshotBatchResult)
        assert len(result.snapshot_keys) == 2
        assert result.counts["players"] == 1
        assert result.counts["monsters"] == 1
        assert result.failed_players == []
        assert result.failed_monsters == []

    async def test_prepare_snapshots_partial_failure(self, service, snapshot_manager, mocker):
        m_player = mocker.patch("src.backend.features.actor_state.runtime.assemblers.player_assembler.build_snapshots",
                               AsyncMock(return_value={1: {"meta": {}}}))
        m_monster = mocker.patch("src.backend.features.actor_state.runtime.assemblers.monster_assembler.build_snapshots",
                                AsyncMock(return_value={"m1": {"meta": {}}}))

        # Only player snapshot saved
        snapshot_manager.save_snapshots = AsyncMock(return_value={
            "s1:player:1": "key1"
        })

        result = await service.prepare_snapshots("s1", [1], ["m1"])

        assert result.counts["players"] == 1
        assert result.counts["monsters"] == 0
        assert result.failed_monsters == ["m1"]

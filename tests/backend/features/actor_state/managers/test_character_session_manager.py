from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.infrastructure.actor_state.managers.session import CharacterSessionManager


@pytest.mark.unit
class TestCharacterSessionManager:
    @pytest.fixture
    def redis(self):
        mock = MagicMock()
        mock.redis_client = MagicMock()
        return mock

    @pytest.fixture
    def manager(self, redis):
        return CharacterSessionManager(redis)

    async def test_unlock_skills_writes_flat_active_skill_objects(self, manager, redis):
        mock_json = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock()
        mock_pipe.json.return_value = mock_json
        redis.redis_client.pipeline.return_value.__aenter__.return_value = mock_pipe

        await manager.unlock_skills(7, ["melee_combat", "intuition", "melee_combat"])

        assert mock_json.set.call_count == 2
        mock_json.set.assert_any_call(
            "game:ac:7",
            "$.skills.melee_combat",
            {"xp": 0.0, "unlocked": True, "state": "PLUS"},
        )
        mock_json.set.assert_any_call(
            "game:ac:7",
            "$.skills.intuition",
            {"xp": 0.0, "unlocked": True, "state": "PLUS"},
        )
        mock_pipe.execute.assert_awaited_once()

    async def test_unlock_skills_skips_empty_payload(self, manager, redis):
        await manager.unlock_skills(7, [])

        redis.redis_client.pipeline.assert_not_called()

    async def test_get_session_normalizes_legacy_attribute_keys(self, manager, redis):
        document = {
            "char_id": 7,
            "attributes": {
                "strength": 8,
                "intelligence": 9,
                "wisdom": 10,
                "men": 11,
                "charisma": 12,
                "luck": 13,
            },
        }
        redis.json_module.get = AsyncMock(return_value=[document])
        redis.json_module.set = AsyncMock()

        session = await manager.get_session(7)

        assert session["attributes"] == {
            "strength": 8,
            "intellect": 9,
            "memory": 10,
            "mental": 11,
            "projection": 12,
            "prediction": 13,
        }
        redis.json_module.set.assert_awaited_once_with("game:ac:7", "$", document)

    async def test_get_session_keeps_new_attribute_keys_without_write(self, manager, redis):
        document = {
            "char_id": 7,
            "attributes": {
                "strength": 8,
                "intellect": 9,
                "memory": 10,
                "mental": 11,
                "projection": 12,
                "prediction": 13,
            },
        }
        redis.json_module.get = AsyncMock(return_value=[document])
        redis.json_module.set = AsyncMock()

        session = await manager.get_session(7)

        assert session == document
        redis.json_module.set.assert_not_awaited()

    async def test_set_world_theme_skips_missing_session_document(self, manager, redis):
        redis.string.exists = AsyncMock(return_value=0)
        manager.patch_fields = AsyncMock()

        await manager.set_world_theme(7, {"loc_id": "52_52"})

        manager.patch_fields.assert_not_awaited()

    async def test_set_world_theme_patches_existing_session_document(self, manager, redis):
        redis.string.exists = AsyncMock(return_value=1)
        manager.patch_fields = AsyncMock()

        await manager.set_world_theme(7, {"loc_id": "52_52"})

        manager.patch_fields.assert_awaited_once_with(7, {"$.world_theme": {"loc_id": "52_52"}})

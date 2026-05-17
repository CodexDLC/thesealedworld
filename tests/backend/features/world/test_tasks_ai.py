from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO
from src.backend.features.world.tasks_ai import (
    WorldLocationBatchTaskHandler,
    WorldZoneLoreTaskHandler,
    build_world_location_batch_task_spec,
    build_world_zone_lore_task_spec,
)


@pytest.mark.unit
async def test_world_zone_lore_task_builds_json_request_and_applies_result(mocker):
    zone = SimpleNamespace(
        id="D4_1_1",
        region_id="D4",
        biome_id="city_ruins",
        tier=0,
        flags={"narrative_context": "Former capital safe hub."},
    )
    spec = build_world_zone_lore_task_spec(zone)
    task = SimpleNamespace(entity_id=zone.id, input_payload=spec.input_payload)
    session = SimpleNamespace(flush=AsyncMock())
    handler = WorldZoneLoreTaskHandler(session=session)

    request = await handler.build_request(task)

    assert request["kind"] == "json"
    assert request["schema"].__name__ == "WorldZoneLoreDTO"
    assert "Former capital safe hub." in request["prompt"].messages[1].content
    assert spec.asset_hash is not None
    assert len(spec.asset_hash) <= 128
    assert "Former capital safe hub." not in spec.asset_hash

    data = mocker.MagicMock()
    data.get_zone = AsyncMock(return_value=zone)
    data.save_zone_lore = AsyncMock()
    mocker.patch("src.backend.features.world.tasks_ai.WorldDataIntegration", return_value=data)

    await handler.apply_result(
        task,
        AIGenerationTaskResultDTO(output_payload={"name": "Сердце Цитадели", "background": "Старый центр столицы."}),
    )

    data.save_zone_lore.assert_awaited_once_with(
        zone,
        lore_name="Сердце Цитадели",
        lore_background="Старый центр столицы.",
    )


@pytest.mark.unit
async def test_world_location_batch_task_builds_json_request_and_updates_nodes(mocker):
    batch = [
        {"id": "45_52", "tags": ["city_ruins_edge", "road"]},
        {"id": "46_52", "tags": ["deep_city_ruins"]},
    ]
    spec = build_world_location_batch_task_spec(batch=batch, district_key="D4_0_1")
    task = SimpleNamespace(entity_id=spec.entity_id, input_payload=spec.input_payload)
    session = SimpleNamespace(flush=AsyncMock())
    handler = WorldLocationBatchTaskHandler(session=session)

    request = await handler.build_request(task)

    assert request["kind"] == "json"
    assert request["schema"].__name__ == "WorldLocationBatchResponseDTO"
    assert "45_52" in request["prompt"].messages[1].content

    data = mocker.MagicMock()
    data.update_content = AsyncMock(return_value=True)
    data.update_flags = AsyncMock()
    mocker.patch("src.backend.features.world.tasks_ai.WorldDataIntegration", return_value=data)

    await handler.apply_result(
        task,
        AIGenerationTaskResultDTO(
            output_payload={
                "locations": [
                    {"id": "45_52", "title": "Запертые Врата", "description": "Монолитная арка."},
                    {"id": "46_52", "title": "Мертвый Проспект", "description": "Дорога к руинам."},
                ]
            }
        ),
    )

    assert data.update_content.await_count == 2
    data.update_flags.assert_any_await(45, 52, {"ai_content_status": "generated"})
    data.update_flags.assert_any_await(46, 52, {"ai_content_status": "generated"})

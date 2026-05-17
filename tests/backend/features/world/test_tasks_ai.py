from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO
from src.backend.features.world.location_images import (
    WORLD_LOCATION_IMAGE_SIZE,
    WORLD_LOCATION_IMAGE_TASK,
    WorldLocationImageTaskHandler,
    build_world_location_image_task_spec,
)
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


@pytest.mark.unit
async def test_world_location_image_task_builds_plain_image_request() -> None:
    spec = build_world_location_image_task_spec(
        loc_id="52_52",
        title="Площадь Рунного Круга",
        description="Центр цитадели.",
        biome_id="city_ruins",
        terrain_type="ancient_pavement",
        environment_tags=["hub_center", "active_portal", "runic_circle", "tents"],
        visual_overrides={
            "image_profile": "d4_capital_hub",
            "node_role": "portal_plaza",
            "composition": "central portal plaza with survivor tents only at the rim",
            "forbidden": ["readable runes"],
        },
    )
    task = SimpleNamespace(entity_id=spec.entity_id, input_payload=spec.input_payload)
    handler = WorldLocationImageTaskHandler()

    request = await handler.build_request(task)

    assert spec.task_type == WORLD_LOCATION_IMAGE_TASK
    assert spec.output_kind == "image"
    assert spec.storage_prefix == "world/locations/d4"
    assert request["kind"] == "image"
    assert request["content_type"] == "image/webp"
    assert request["target_size"] == WORLD_LOCATION_IMAGE_SIZE
    assert request["storage_key"].startswith("world/locations/d4/52_52_")
    assert "ancient technomagical sacred architecture" in request["prompt"]
    assert "Aur-Entar is the last capital" in request["prompt"]
    assert "NODE_ROLE (portal_plaza)" in request["prompt"]
    assert "no characters" in request["prompt"]
    assert "readable runes" in request["prompt"]


@pytest.mark.unit
async def test_world_location_image_task_applies_result_to_node_content(mocker):
    node = SimpleNamespace(
        content={
            "title": "Площадь Рунного Круга",
            "description": "Центр цитадели.",
            "background_url": "/static/images/exploration/city/d4/52_52_runic_circle_plaza.png",
        }
    )
    data = mocker.MagicMock()
    data.get_node = AsyncMock(return_value=node)
    data.update_content = AsyncMock(return_value=True)
    data.update_flags = AsyncMock()
    mocker.patch("src.backend.features.world.location_images.tasks.WorldDataIntegration", return_value=data)
    session = SimpleNamespace(flush=AsyncMock())
    handler = WorldLocationImageTaskHandler(session=session)
    task = SimpleNamespace(entity_id="52_52", input_payload={"loc_id": "52_52"})

    await handler.apply_result(
        task,
        AIGenerationTaskResultDTO(
            storage_key="world/locations/d4/52_52_hash.webp",
            generated_url="/static/generated-assets/world/locations/d4/52_52_hash.webp",
            asset_hash="hash",
            storage_backend="local",
            content_type="image/webp",
            size_bytes=123,
            metadata={"width": 1536, "height": 864},
        ),
    )

    updated = data.update_content.await_args.args[2]
    assert updated["background_url"] == "/static/generated-assets/world/locations/d4/52_52_hash.webp"
    assert updated["visual"]["status"] == "generated"
    assert updated["visual"]["previous_background_url"] == "/static/images/exploration/city/d4/52_52_runic_circle_plaza.png"
    assert updated["visual"]["width"] == 1536
    assert updated["visual"]["height"] == 864
    data.update_flags.assert_awaited_once_with(52, 52, {"ai_image_status": "generated"})
    session.flush.assert_awaited_once()

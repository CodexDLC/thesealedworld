from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO
from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO
from src.backend.features.items.tasks_ai import ItemTextTaskHandler, build_item_text_task_spec


def _item() -> GeneratedItemDTO:
    return GeneratedItemDTO(
        instance_id="item-1",
        template_id="warhammer",
        item_type="weapon",
        rarity="uncommon",
        rarity_tier=1,
        name="Ржавый боевой молот",
        description="Старое описание.",
        base_id="warhammer",
        power=10,
        durability_max=100,
        slot="two_hand",
        metadata={"item_grade": "uncommon"},
    )


@pytest.mark.unit
async def test_item_text_task_builds_json_request_and_applies_result(mocker):
    request = ItemGenerationRequestDTO(base_id="warhammer", rarity_tier=1, request_ai_text=True)
    spec = build_item_text_task_spec(item_id="item-1", request=request)
    task = SimpleNamespace(entity_id="item-1", input_payload=spec.input_payload)
    session = SimpleNamespace()
    handler = ItemTextTaskHandler(session=session)

    persistence = mocker.MagicMock()
    persistence.get_generated_item = AsyncMock(return_value=_item())
    persistence.save_generated_text = AsyncMock()
    mocker.patch("src.backend.features.items.tasks_ai.ItemPersistenceIntegration", return_value=persistence)

    provider_request = await handler.build_request(task)

    assert provider_request["kind"] == "json"
    assert provider_request["schema"].__name__ == "GeneratedItemTextDTO"
    assert "warhammer" in provider_request["prompt"].messages[1].content

    await handler.apply_result(
        task,
        AIGenerationTaskResultDTO(
            output_payload={"name": "Молот Памяти", "description": "Тяжелый молот с холодной рукоятью."}
        ),
    )

    persistence.save_generated_text.assert_awaited_once()
    saved_item = persistence.save_generated_text.await_args.args[1]
    assert saved_item.name == "Молот Памяти"
    assert saved_item.metadata["ai_text_status"] == "generated"

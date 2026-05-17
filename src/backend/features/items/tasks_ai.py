from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO
from src.backend.features.items.dto.ai import GeneratedItemTextDTO
from src.backend.features.items.dto.instance import ItemGenerationRequestDTO
from src.backend.features.items.integrations.persistence import ItemPersistenceIntegration
from src.backend.features.items.prompts.router import build_item_name_description_prompt
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.items.services.text_service import ItemTextService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.generation_ai.registry import AIGenerationTaskRegistry

ITEM_TEXT_TASK = "items.text"


class ItemTextTaskHandler:
    task_type = ITEM_TEXT_TASK

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def build_request(self, task: Any) -> dict[str, Any]:
        if self.session is None:
            raise RuntimeError("ItemTextTaskHandler requires a database session to build request")

        request = ItemGenerationRequestDTO.model_validate((task.input_payload or {}).get("request") or {})
        persistence = ItemPersistenceIntegration(ItemInstanceRepository(self.session))
        item = await persistence.get_generated_item(str(task.entity_id))
        if item is None:
            raise ValueError(f"Generated item not found: {task.entity_id}")

        payload = ItemTextService()._build_payload(item, request)
        return {
            "kind": "json",
            "prompt": build_item_name_description_prompt(payload),
            "schema": GeneratedItemTextDTO,
        }

    async def apply_result(self, task: Any, result: AIGenerationTaskResultDTO) -> None:
        if self.session is None:
            raise RuntimeError("ItemTextTaskHandler requires a database session to apply result")

        generated = GeneratedItemTextDTO.model_validate(result.output_payload)
        persistence = ItemPersistenceIntegration(ItemInstanceRepository(self.session))
        item = await persistence.get_generated_item(str(task.entity_id))
        if item is None:
            raise ValueError(f"Generated item not found: {task.entity_id}")
        enriched = item.model_copy(
            update={
                "name": generated.name,
                "description": generated.description,
                "metadata": {
                    **item.metadata,
                    "ai_text_status": "generated",
                    "ai_prompt": "item_name_description",
                },
            }
        )
        await persistence.save_generated_text(str(task.entity_id), enriched)


def build_item_text_task_spec(
    *,
    item_id: str,
    request: ItemGenerationRequestDTO,
) -> AIGenerationTaskSpecDTO:
    request_payload = request.model_dump(mode="json")
    return AIGenerationTaskSpecDTO(
        task_type=ITEM_TEXT_TASK,
        entity_type="item",
        entity_id=str(item_id),
        output_kind="json",
        input_payload={"item_id": str(item_id), "request": request_payload},
        asset_hash=f"{item_id}:{request_payload.get('rarity_tier')}:{request_payload.get('source')}",
        priority=80,
        max_attempts=4,
        metadata={"item_id": str(item_id), "source": request.source},
    )


def register_generation_ai_tasks(registry: AIGenerationTaskRegistry, *, session: AsyncSession | None = None) -> None:
    registry.register(ItemTextTaskHandler(session=session))

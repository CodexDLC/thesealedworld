from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.backend.config.settings import settings
from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO
from src.backend.features.world.integrations import WorldDataIntegration
from src.backend.features.world.prompts import build_location_image_prompt
from src.backend.infrastructure.world.repositories import WorldRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

WORLD_LOCATION_IMAGE_TASK = "world.location_image"
WORLD_LOCATION_IMAGE_SIZE = {"width": 1536, "height": 864}
WORLD_LOCATION_IMAGE_STORAGE_ROOT = "world/locations"


class WorldLocationImageTaskHandler:
    task_type = WORLD_LOCATION_IMAGE_TASK

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def build_request(self, task: Any) -> dict[str, Any]:
        payload = dict(task.input_payload or {})
        storage_key = str(payload.get("storage_key") or "")
        if not storage_key:
            raise ValueError("World location image task requires storage_key")
        return {
            "kind": "image",
            "prompt": build_location_image_prompt(payload),
            "model": payload.get("image_model") or settings.gemini_location_image_model,
            "content_type": "image/webp",
            "storage_key": storage_key,
            "target_size": dict(WORLD_LOCATION_IMAGE_SIZE),
        }

    async def apply_result(self, task: Any, result: AIGenerationTaskResultDTO) -> None:
        if self.session is None:
            raise RuntimeError("WorldLocationImageTaskHandler requires a database session to apply result")

        payload = dict(task.input_payload or {})
        loc_id = str(payload.get("loc_id") or task.entity_id)
        try:
            x, y = map(int, loc_id.split("_"))
        except ValueError as exc:
            raise ValueError(f"Invalid world location image entity id: {loc_id}") from exc

        data = WorldDataIntegration(WorldRepository(self.session))
        node = await data.get_node(x, y)
        if node is None:
            raise ValueError(f"World node not found for image result: {loc_id}")
        if not result.generated_url:
            raise ValueError(f"World location image result missing generated_url: {loc_id}")

        content = dict(node.content or {})
        previous_background_url = content.get("background_url")
        content["background_url"] = result.generated_url
        visual = dict(content.get("visual") or {})
        visual.update(
            {
                "status": "generated",
                "source": "ai_generated",
                "image_url": result.generated_url,
                "generated_image_url": result.generated_url,
                "previous_background_url": previous_background_url,
                "storage_key": result.storage_key,
                "asset_hash": result.asset_hash,
                "storage_backend": result.storage_backend,
                "content_type": result.content_type,
                "size_bytes": result.size_bytes,
                "width": result.metadata.get("width"),
                "height": result.metadata.get("height"),
            }
        )
        content["visual"] = visual
        if not await data.update_content(x, y, content):
            raise RuntimeError(f"Failed to update world location image content: {loc_id}")
        await data.update_flags(x, y, {"ai_image_status": "generated"})
        await self.session.flush()


def build_world_location_image_task_spec(
    *,
    loc_id: str,
    title: str,
    description: str,
    biome_id: str,
    terrain_type: str,
    environment_tags: list[str],
    visual_overrides: dict[str, Any] | None = None,
    region_id: str = "D4",
    image_model: str | None = None,
    prompt_contract_version: str | None = None,
) -> AIGenerationTaskSpecDTO:
    visual_overrides = dict(visual_overrides or {})
    asset_payload = {
        "loc_id": loc_id,
        "title": title,
        "description": description,
        "biome_id": biome_id,
        "terrain_type": terrain_type,
        "environment_tags": list(environment_tags),
        "visual_overrides": visual_overrides,
        "image_model": image_model or settings.gemini_location_image_model,
    }
    if prompt_contract_version:
        asset_payload["prompt_contract_version"] = prompt_contract_version
    asset_hash = _short_asset_hash("world.location_image", asset_payload)
    storage_key = (
        f"{WORLD_LOCATION_IMAGE_STORAGE_ROOT}/{region_id.lower()}/{loc_id}_{asset_hash.rsplit(':', 1)[-1]}.webp"
    )
    return AIGenerationTaskSpecDTO(
        task_type=WORLD_LOCATION_IMAGE_TASK,
        entity_type="world_location",
        entity_id=loc_id,
        output_kind="image",
        input_payload={
            **asset_payload,
            "storage_key": storage_key,
        },
        asset_hash=asset_hash,
        storage_prefix=f"{WORLD_LOCATION_IMAGE_STORAGE_ROOT}/{region_id.lower()}",
        priority=75,
        max_attempts=3,
        metadata={
            "region_id": region_id,
            "loc_id": loc_id,
            "visual_asset_hash": asset_hash,
        },
    )


def _short_asset_hash(namespace: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"{namespace}:{digest}"

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO
from src.backend.features.world.dto.ai import WorldLocationBatchResponseDTO, WorldZoneLoreDTO
from src.backend.features.world.integrations import WorldDataIntegration
from src.backend.features.world.prompts import build_batch_location_desc_prompt, build_zone_lore_prompt
from src.backend.infrastructure.world.repositories import WorldRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.generation_ai.registry import AIGenerationTaskRegistry
    from src.backend.features.world.integrations import WorldZoneSeed

WORLD_ZONE_LORE_TASK = "world.zone_lore"
WORLD_LOCATION_BATCH_TASK = "world.location_batch"


class WorldZoneLoreTaskHandler:
    task_type = WORLD_ZONE_LORE_TASK

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def build_request(self, task: Any) -> dict[str, Any]:
        payload = dict(task.input_payload or {})
        return {
            "kind": "json",
            "prompt": build_zone_lore_prompt(
                region_id=str(payload["region_id"]),
                biome_id=str(payload["biome_id"]),
                tier=int(payload["tier"]),
                narrative_context=payload.get("narrative_context"),
            ),
            "schema": WorldZoneLoreDTO,
        }

    async def apply_result(self, task: Any, result: AIGenerationTaskResultDTO) -> None:
        if self.session is None:
            raise RuntimeError("WorldZoneLoreTaskHandler requires a database session to apply result")

        data = WorldDataIntegration(WorldRepository(self.session))
        zone = await data.get_zone(str(task.entity_id))
        if zone is None:
            raise ValueError(f"World zone not found: {task.entity_id}")

        lore = WorldZoneLoreDTO.model_validate(result.output_payload)
        await data.save_zone_lore(zone, lore_name=lore.name, lore_background=lore.background)
        await self.session.flush()


class WorldLocationBatchTaskHandler:
    task_type = WORLD_LOCATION_BATCH_TASK

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def build_request(self, task: Any) -> dict[str, Any]:
        payload = dict(task.input_payload or {})
        batch = list(payload.get("batch") or [])
        if not batch:
            raise ValueError("World location batch task requires non-empty batch")
        return {
            "kind": "json",
            "prompt": build_batch_location_desc_prompt(batch),
            "schema": WorldLocationBatchResponseDTO,
        }

    async def apply_result(self, task: Any, result: AIGenerationTaskResultDTO) -> None:
        if self.session is None:
            raise RuntimeError("WorldLocationBatchTaskHandler requires a database session to apply result")

        payload = dict(task.input_payload or {})
        batch = list(payload.get("batch") or [])
        generated = WorldLocationBatchResponseDTO.model_validate(result.output_payload)
        result_map = {
            item.id: {
                "title": item.title,
                "description": item.description,
            }
            for item in generated.locations
        }
        expected_ids = {str(item["id"]) for item in batch if isinstance(item, dict) and item.get("id")}
        actual_ids = set(result_map)
        if expected_ids - actual_ids:
            raise ValueError(f"World location batch missing ids: {sorted(expected_ids - actual_ids)}")

        data = WorldDataIntegration(WorldRepository(self.session))
        for item in batch:
            if not isinstance(item, dict):
                continue
            loc_id = str(item.get("id") or "")
            text_data = result_map.get(loc_id)
            if not text_data:
                continue
            try:
                x, y = map(int, loc_id.split("_"))
            except ValueError:
                continue
            updated = await data.update_content(
                x,
                y,
                {
                    "title": text_data["title"],
                    "description": text_data["description"],
                    "environment_tags": list(item.get("tags") or []),
                },
            )
            if updated:
                await data.update_flags(x, y, {"ai_content_status": "generated"})
        await self.session.flush()


def build_world_zone_lore_task_spec(zone: WorldZoneSeed) -> AIGenerationTaskSpecDTO:
    narrative_context = zone.flags.get("narrative_context") if isinstance(zone.flags, dict) else None
    asset_hash = _short_asset_hash(
        "world.zone_lore",
        {
            "zone_id": zone.id,
            "region_id": zone.region_id,
            "biome_id": zone.biome_id,
            "tier": zone.tier,
            "narrative_context": narrative_context,
        },
    )
    return AIGenerationTaskSpecDTO(
        task_type=WORLD_ZONE_LORE_TASK,
        entity_type="world_zone",
        entity_id=zone.id,
        output_kind="json",
        input_payload={
            "zone_id": zone.id,
            "region_id": zone.region_id,
            "biome_id": zone.biome_id,
            "tier": zone.tier,
            "narrative_context": narrative_context,
        },
        asset_hash=asset_hash,
        priority=40,
        max_attempts=4,
        metadata={"zone_id": zone.id, "region_id": zone.region_id},
    )


def build_world_location_batch_task_spec(
    *,
    batch: list[dict[str, Any]],
    district_key: str,
) -> AIGenerationTaskSpecDTO:
    first_id = str(batch[0]["id"]) if batch else "empty"
    last_id = str(batch[-1]["id"]) if batch else "empty"
    batch_ids = [str(item["id"]) for item in batch]
    return AIGenerationTaskSpecDTO(
        task_type=WORLD_LOCATION_BATCH_TASK,
        entity_type="world_location_batch",
        entity_id=f"{district_key}:{first_id}:{last_id}",
        output_kind="json",
        input_payload={"district_key": district_key, "batch": batch},
        asset_hash=":".join(batch_ids),
        priority=60,
        max_attempts=4,
        metadata={"district_key": district_key, "location_ids": batch_ids},
    )


def register_generation_ai_tasks(registry: AIGenerationTaskRegistry, *, session: AsyncSession | None = None) -> None:
    registry.register(WorldZoneLoreTaskHandler(session=session))
    registry.register(WorldLocationBatchTaskHandler(session=session))


def _short_asset_hash(namespace: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"{namespace}:{digest}"

import asyncio
import json
import traceback

from loguru import logger as log

from src.backend.database.postgres.repositories import IWorldRepo
from src.backend.services.gemini_service.gemini_service import gemini_answer


class ContentGenerationService:
    def __init__(self, world_repo: IWorldRepo):
        self.repo = world_repo
        self.batch_size = 5

    async def generate_content_for_path(self, path_coords: list[tuple[int, int]]):
        total_nodes = len(path_coords)
        log.info(f"ContentGen | task=started nodes={total_nodes} batch_size={self.batch_size} mode=sequential")

        chunks = [path_coords[i : i + self.batch_size] for i in range(0, total_nodes, self.batch_size)]
        log.info(f"ContentGen | action=batching total_batches={len(chunks)}")

        for i, chunk in enumerate(chunks):
            log.info(f"ContentGen | processing_batch {i + 1}/{len(chunks)}...")
            await self._process_batch(chunk, batch_id=i + 1)
            await asyncio.sleep(1.0)

        log.info("ContentGen | task=finished")

    async def _process_batch(self, chunk: list[tuple[int, int]], batch_id: int):
        payload = []

        for x, y in chunk:
            node = await self.repo.get_node(x, y)
            if not node:
                continue

            my_tags = []
            if node.content and isinstance(node.content, dict):
                my_tags = node.content.get("environment_tags", [])

            surroundings = await self._get_surroundings_context(x, y)

            item = {
                "id": f"{x}_{y}",
                "internal_tags": my_tags,
                "surroundings": surroundings,
            }
            payload.append(item)

        if not payload:
            return

        response_text = ""
        try:
            user_text = json.dumps(payload, ensure_ascii=False)
            log.debug(
                f"ContentGen | batch={batch_id} action=sending_request items={len(payload)} payload_preview:\n{user_text[:500]}"
            )
            response_text = await gemini_answer(
                mode="batch_location_desc",
                user_text=user_text,
                max_tokens=4000,
            )
            log.debug(f"ContentGen | batch={batch_id} action=received_response raw_response:\n{response_text}")
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            if not clean_json:
                raise ValueError("Empty response from LLM")
            result_map = json.loads(clean_json)

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            log.error(
                f"ContentGen | batch={batch_id} status=llm_error exception='{e}' raw_preview='{response_text[:100]}'"
            )
            log.error(traceback.format_exc())
            return

        saved_count = 0
        for loc_id, data in result_map.items():
            try:
                content = data.get("content", {})
                x, y = map(int, loc_id.split("_"))

                original_item = next((i for i in payload if i["id"] == loc_id), None)
                tags = original_item["internal_tags"] if original_item else []

                final_content = {
                    "title": content.get("title", "Пустошь"),
                    "description": content.get("description", "..."),
                    "environment_tags": tags,
                }

                await self.repo.update_content(x, y, final_content)
                saved_count += 1

            except (ValueError, TypeError, KeyError) as e:
                log.error(f"ContentGen | save_error id={loc_id} err={e}")

        log.info(f"ContentGen | batch={batch_id} status=saved count={saved_count}/{len(chunk)}")

    async def _get_surroundings_context(self, x: int, y: int) -> dict[str, list[str]]:
        directions = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
        result = {}

        for dir_name, (dx, dy) in directions.items():
            nx, ny = x + dx, y + dy
            node = await self.repo.get_node(nx, ny)

            if node:
                tags = []
                if node.content and isinstance(node.content, dict):
                    tags = node.content.get("environment_tags", [])

                if node.flags and node.flags.get("is_safe_zone"):
                    tags.append("safe_zone")

                if tags:
                    result[dir_name] = tags
            else:
                result[dir_name] = ["void"]

        return result

    async def generate_from_orchestrator(self, payload_items: list[dict]) -> dict | None:
        """
        Принимает готовый payload от ZoneOrchestrator и отправляет его в LLM.
        """
        if not payload_items:
            return None

        response_text = ""
        try:
            user_text = json.dumps(payload_items, ensure_ascii=False)
            log.debug(
                f"ContentGen | orchestrator_mode action=sending_request items={len(payload_items)} payload_preview:\n{user_text[:500]}"
            )
            response_text = await gemini_answer(
                mode="batch_location_desc",
                user_text=user_text,
                max_tokens=4000,
            )
            log.debug(f"ContentGen | orchestrator_mode action=received_response raw_response:\n{response_text}")
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            if not clean_json:
                raise ValueError("Empty response from LLM")

            result_map = json.loads(clean_json)
            return result_map

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            log.error(
                f"ContentGen | orchestrator_mode status=llm_error exception='{e}' raw_preview='{response_text[:100]}'"
            )
            log.error(traceback.format_exc())
            return None

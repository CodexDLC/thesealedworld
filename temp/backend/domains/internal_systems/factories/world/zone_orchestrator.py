import json
import math

from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.db_contract.i_world_repo import IWorldRepo
from src.backend.domains.internal_systems.factories.monster.clan_factory import ClanFactory
from src.backend.domains.internal_systems.factories.world.content_gen_service import (
    ContentGenerationService,
)
from src.backend.domains.internal_systems.factories.world.threat_service import ThreatService
from src.backend.resources.game_data.graf_data_world.world_config import (
    ANCHORS,
    HUB_CENTER,
    REGION_ROWS,
    REGION_SIZE,
    ROAD_TAGS,
    VISUAL_DOMINANTS,
    ZONE_SIZE,
)


class ZoneOrchestrator:
    def __init__(self, session: AsyncSession, repo: IWorldRepo, content_service: ContentGenerationService):
        self.session = session
        self.repo = repo
        self.content_service = content_service
        self.clan_factory = ClanFactory(session)
        self.chunk_size = 5

    def _get_zone_id(self, x: int, y: int) -> str:
        col = (x // REGION_SIZE) + 1
        row_idx = min(y // REGION_SIZE, len(REGION_ROWS) - 1)
        region_id = f"{REGION_ROWS[row_idx]}{col}"
        local_x = x % REGION_SIZE
        local_y = y % REGION_SIZE
        zone_x = local_x // ZONE_SIZE
        zone_y = local_y // ZONE_SIZE
        return f"{region_id}_{zone_x}_{zone_y}"

    def _get_structural_tags(self, x: int, y: int, start_x: int, start_y: int, main_biome: str) -> list[str]:
        structural_tags = []
        local_x = x - start_x
        local_y = y - start_y
        center = self.chunk_size // 2
        is_edge = local_x == 0 or local_x == self.chunk_size - 1 or local_y == 0 or local_y == self.chunk_size - 1
        is_center = local_x == center and local_y == center
        if is_center:
            structural_tags.append(f"{main_biome}_center")
        elif is_edge:
            structural_tags.append(f"{main_biome}_edge")
        else:
            structural_tags.append(f"deep_{main_biome}")
        return structural_tags

    async def generate_chunk(self, center_x: int, center_y: int) -> bool:
        log.info(f"ZoneOrchestrator | start_chunk center={center_x}:{center_y}")

        half = self.chunk_size // 2
        start_x = center_x - half
        start_y = center_y - half
        scan_width = self.chunk_size + 2
        scan_height = self.chunk_size + 2

        try:
            grid_nodes = await self.repo.get_nodes_in_rect(start_x - 1, start_y - 1, scan_width, scan_height)
        except SQLAlchemyError as e:
            log.error(f"ZoneOrchestrator | db_error: {e}")
            return False

        node_map = {(n.x, n.y): n for n in grid_nodes}
        payload_items = []

        for x in range(start_x, start_x + self.chunk_size):
            for y in range(start_y, start_y + self.chunk_size):
                current_node = node_map.get((x, y))

                if current_node and current_node.terrain_type == "static_structure":
                    continue

                base_tags = []
                if current_node and current_node.content and isinstance(current_node.content, dict):
                    base_tags = current_node.content.get("environment_tags", [])

                main_biome = base_tags[0] if base_tags else "wasteland"
                structural_tags = self._get_structural_tags(x, y, start_x, start_y, main_biome)
                influence_tags = ThreatService.get_narrative_tags(x, y)
                narrative_tags = list(set(base_tags + structural_tags + influence_tags))

                context_hints = self._scan_surroundings(x, y, node_map) + self._scan_global_landmarks(x, y)

                if self._check_incoming_roads(x, y, node_map) and "road" not in narrative_tags:
                    narrative_tags.append("road")
                    try:
                        await self.repo.update_flags(x, y, {"has_road": True})
                    except SQLAlchemyError as e:
                        log.warning(f"Failed to update road flag for ({x},{y}): {e}")

                payload_items.append({"id": f"{x}_{y}", "tags": narrative_tags, "context": context_hints})

        if not payload_items:
            return True

        log.info(f"ZoneOrchestrator | sending_to_llm items={len(payload_items)}")
        raw_response = await self.content_service.generate_from_orchestrator(payload_items)
        if not raw_response:
            return False

        unique_zones_context = {}
        save_errors = 0
        for loc_id, text_data in raw_response.items():
            try:
                x, y = map(int, loc_id.split("_"))

                original_item = next((i for i in payload_items if i["id"] == loc_id), None)
                final_tags = original_item["tags"] if original_item else []

                final_content = {
                    "title": text_data.get("title", "Пустошь"),
                    "description": text_data.get("description", "..."),
                    "environment_tags": final_tags,
                }

                node_to_update = node_map.get((x, y))
                flags = node_to_update.flags if node_to_update else {}
                terrain = node_to_update.terrain_type if node_to_update else "flat"
                zone_id = self._get_zone_id(x, y)

                if terrain == "static_structure":
                    continue

                await self.repo.create_or_update_node(
                    x=x, y=y, zone_id=zone_id, terrain_type=terrain, is_active=True, content=final_content, flags=flags
                )

                if zone_id not in unique_zones_context:
                    zone_db = await self.repo.get_zone(zone_id)
                    if zone_db:
                        true_biome = zone_db.biome_id
                        true_tier = zone_db.tier
                        is_safe = zone_db.flags.get("is_safe_zone", False)
                    else:
                        true_biome = "wasteland"
                        true_tier = flags.get("threat_tier", 0)
                        is_safe = False

                    unique_zones_context[zone_id] = {
                        "tier": true_tier,
                        "biome": true_biome,
                        "tags": final_tags,
                        "anchor_key": f"{zone_id}_{true_biome}",
                        "is_safe": is_safe,
                    }

            except (ValueError, SQLAlchemyError) as e:
                log.error(f"ZoneOrchestrator | save_error id={loc_id} error={e}")
                save_errors += 1

        for z_id, ctx in unique_zones_context.items():
            if ctx.get("is_safe", False):
                log.info(f"ZoneOrchestrator | Zone {z_id} is SAFE ZONE. Skipping population.")
                continue

            log.info(f"ZoneOrchestrator | Populating Zone {z_id} (Tier {ctx['tier']})...")

            await self.clan_factory.ensure_population_for_zone(
                tier=ctx["tier"], biome_id=ctx["biome"], location_tags=ctx["tags"], zone_id=z_id
            )

        if save_errors > 0:
            return False
        log.info("ZoneOrchestrator | chunk_complete")
        return True

    def _scan_surroundings(self, x: int, y: int, node_map: dict) -> list[str]:
        hints = []
        directions = [
            (0, -1, "севере"),
            (0, 1, "юге"),
            (-1, 0, "западе"),
            (1, 0, "востоке"),
            (1, 1, "юго-востоке"),
            (1, -1, "северо-востоке"),
            (-1, 1, "юго-западе"),
            (-1, -1, "северо-западе"),
        ]
        for dx, dy, side_name in directions:
            neighbor = node_map.get((x + dx, y + dy))
            if not neighbor or not neighbor.content:
                continue
            n_content = neighbor.content
            if isinstance(n_content, str):
                try:
                    n_content = json.loads(n_content)
                except json.JSONDecodeError:
                    n_content = {}
            n_tags = n_content.get("environment_tags", [])
            for _category, tags in VISUAL_DOMINANTS.items():
                for tag in tags:
                    if tag in n_tags:
                        hints.append(f"На {side_name} виднеется {tag}")
                        break
        return hints

    def _scan_global_landmarks(self, x: int, y: int) -> list[str]:
        hints = []
        landmarks = [
            {"name": "Шпиль Хаба", "x": HUB_CENTER["x"], "y": HUB_CENTER["y"]},
            {"name": "Ледяной Пик", "x": ANCHORS[0]["x"], "y": ANCHORS[0]["y"]},
            {"name": "Дымящийся Вулкан", "x": ANCHORS[1]["x"], "y": ANCHORS[1]["y"]},
            {"name": "Гравитационная Аномалия", "x": ANCHORS[2]["x"], "y": ANCHORS[2]["y"]},
            {"name": "Живые Джунгли", "x": ANCHORS[3]["x"], "y": ANCHORS[3]["y"]},
        ]
        for landmark in landmarks:
            lm_x_val = landmark.get("x")
            lm_y_val = landmark.get("y")
            if not isinstance(lm_x_val, (int, float)) or not isinstance(lm_y_val, (int, float)):
                continue
            lm_x = int(lm_x_val)
            lm_y = int(lm_y_val)
            dist = math.sqrt((x - lm_x) ** 2 + (y - lm_y) ** 2)
            if dist < 35:
                dx = lm_x - x
                dy = lm_y - y
                direction = ("востоке" if dx > 0 else "западе") if abs(dx) > abs(dy) else "юге" if dy > 0 else "севере"
                if dist < 5:
                    proximity = "совсем рядом"
                elif dist < 15:
                    proximity = "неподалеку"
                else:
                    proximity = "вдалеке"
                hints.append(f"{proximity.capitalize()} на {direction} виднеется {landmark['name']}.")
        return hints

    def _check_incoming_roads(self, x: int, y: int, node_map: dict) -> bool:
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            neighbor = node_map.get((x + dx, y + dy))
            if neighbor and neighbor.content:
                n_content = neighbor.content if isinstance(neighbor.content, dict) else {}
                n_tags = n_content.get("environment_tags", [])
                if any(r in n_tags for r in ROAD_TAGS):
                    return True
        return False

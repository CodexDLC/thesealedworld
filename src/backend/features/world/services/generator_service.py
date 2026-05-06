import asyncio
import json
import logging
from collections.abc import Iterable
from typing import Any

from src.backend.core.ai import AIService
from src.backend.features.world.integrations import WorldDataIntegration
from src.backend.features.world.loaders.village_loader import VillageLoader
from src.backend.features.world.prompts.router import world_prompt_router
from src.backend.features.world.resources.static.start_village import STATIC_LOCATIONS
from src.backend.features.world.runtime.config import HUB_CENTER, REGION_ROWS, REGION_SIZE, ZONE_SIZE
from src.backend.features.world.runtime.theme import WorldThemeService
from src.backend.features.world.runtime.threat import ThreatService

log = logging.getLogger(__name__)

D4_CONTENT_BATCH_SIZE = 25
D4_CONTENT_RETRY_DELAYS_SECONDS = (2.0, 6.0, 15.0)
ZONE_LORE_RETRY_DELAYS_SECONDS = (2.0, 6.0)


class LLMWorldGenerator:
    """Orchestrates world generation using static loaders and AI-driven content."""

    def __init__(self, data: WorldDataIntegration, ai: AIService | None) -> None:
        self.data = data
        self.village_loader = VillageLoader(data)
        self.ai = ai

        # Register world-specific prompts
        if self.ai is not None:
            self.ai.include_router(world_prompt_router)

    async def run(self, mode: str = "test") -> None:
        """Runs the generation process.

        1. Load static village.
        2. Generate surrounding regions and zones.
        3. Populate with AI content if enabled.
        """
        log.info("Starting world generation (mode=%s)", mode)

        # 1. Generate Shell (Regions/Zones)
        if mode == "full":
            await self._generate_world_shell()

        # 2. Generate the first playable territory (D4 old capital).
        await self._generate_d4_capital()

        # 3. Load static hub/village nodes over the generated D4 skeleton.
        await self.village_loader.load_village(STATIC_LOCATIONS)

        # 4. AI Enrichment (Example for Hub Zone)
        if self.ai and mode != "test":
            await self._enrich_zone_with_ai("D4_1_1")
            await self._enrich_d4_capital_nodes_with_ai()

    async def _generate_d4_capital(self) -> None:
        """Generate the first playable territory: D4 old capital, 15x15 nodes."""
        region_id = "D4"
        d4_row_idx = REGION_ROWS.index("D")
        min_x = (4 - 1) * REGION_SIZE
        min_y = d4_row_idx * REGION_SIZE
        max_x = min_x + REGION_SIZE - 1
        max_y = min_y + REGION_SIZE - 1
        mid_x = min_x + REGION_SIZE // 2
        mid_y = min_y + REGION_SIZE // 2

        await self.data.upsert_region(region_id, climate_tags=["ancient_city", "city_ruins", "portal_shield"])

        zones_per_region = REGION_SIZE // ZONE_SIZE
        for zx in range(zones_per_region):
            for zy in range(zones_per_region):
                is_hub_zone = zx == 1 and zy == 1
                zone_id = f"{region_id}_{zx}_{zy}"
                await self.data.upsert_zone(
                    zone_id,
                    region_id=region_id,
                    biome_id="hub_district" if is_hub_zone else "city_ruins",
                    tier=0,
                    flags={
                        "is_safe_zone": is_hub_zone,
                        "is_hub": is_hub_zone,
                        "portal_shield": is_hub_zone,
                        "is_old_capital": True,
                        "threat_tier": 0,
                    },
                )

        await self.data.flush()

        nodes: list[dict[str, Any]] = []
        road_cells = self._build_d4_road_cells(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                nodes.append(
                    self._build_d4_node(
                        x=x,
                        y=y,
                        min_x=min_x,
                        min_y=min_y,
                        max_x=max_x,
                        max_y=max_y,
                        mid_x=mid_x,
                        mid_y=mid_y,
                        road_cells=road_cells,
                    )
                )

        await self.data.bulk_upsert_nodes(nodes)
        log.info("D4 capital generated: %d nodes", len(nodes))

    def _build_d4_node(
        self,
        *,
        x: int,
        y: int,
        min_x: int,
        min_y: int,
        max_x: int,
        max_y: int,
        mid_x: int,
        mid_y: int,
        road_cells: set[tuple[int, int]],
    ) -> dict[str, Any]:
        local_x = x - min_x
        local_y = y - min_y
        zone_id = f"D4_{local_x // ZONE_SIZE}_{local_y // ZONE_SIZE}"
        is_hub = self._is_d4_hub_node(x, y)
        is_boundary = x in (min_x, max_x) or y in (min_y, max_y)
        is_outer_gate = is_boundary and (x == mid_x or y == mid_y)
        is_outer_wall = is_boundary and not is_outer_gate
        has_road = (x, y) in road_cells

        terrain_type = "city_ruins"
        tags = ["ancient_city", "city_ruins"]
        title = "Руины Старой Столицы"
        description = (
            "Мертвый квартал древней столицы. Координата описывает не размер, а отдельную "
            "навигационную область: улицу, площадь, двор или фрагмент квартала."
        )
        flags: dict[str, Any] = {
            "is_active": True,
            "is_safe_zone": is_hub,
            "is_old_capital": True,
            "is_passable": True,
            "threat_tier": 0 if is_hub else 1,
            "travel_cost": 1.0 if is_hub else 1.25,
        }

        if is_hub:
            terrain_type = "ancient_pavement"
            tags.extend(["hub_district", "safe_zone"])
            title = "Внутренний район Цитадели"
            description = "Безопасный внутренний район старой столицы под защитой портального щита."
            flags["travel_cost"] = 1.0

        if is_outer_wall:
            blocked_exits = self._d4_boundary_blocked_exits(
                x=x, y=y, min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y
            )
            terrain_type = "outer_monolith_wall_walk"
            tags.extend(["outer_monolith_wall", "wall_walk", "region_boundary"])
            title = "Ход внешней монолитной стены"
            description = (
                "Край старой столицы здесь занят широкой монолитной стеной. По каменному ходу можно "
                "двигаться вдоль периметра, но наружная сторона закрыта неприступным обрывом кладки."
            )
            flags.update(
                {
                    "blocked_exits": blocked_exits,
                    "boundary_features": self._d4_boundary_features(
                        blocked_exits,
                        kind="outer_monolith_wall",
                        state="sealed",
                        tags=["monolithic_wall", "old_capital_outer_wall", "wall_walk"],
                    ),
                    "travel_cost": 1.0,
                }
            )

        if is_outer_gate:
            direction = self._d4_gate_direction(x=x, y=y, min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)
            terrain_type = "city_gate_outer"
            tags.extend(["gate", "road", "locked_exit"])
            title = f"{self._ru_direction(direction)} внешние ворота D4"
            description = "Ворота в стене старой столицы. Проход существует, но на старте заблокирован."
            flags.update(
                {
                    "is_gate": True,
                    "gate_direction": direction,
                    "exit_locked": True,
                    "unlock_condition": "world_gate_unlock",
                    "gated_exits": {
                        direction: {
                            "kind": "outer_city_gate",
                            "state": "locked",
                            "unlock_condition": "world_gate_unlock",
                            "tags": ["city_gate", "sealed_gate", "old_capital_outer_wall"],
                        }
                    },
                    "boundary_features": {
                        direction: {
                            "kind": "outer_city_gate",
                            "state": "locked",
                            "tags": ["city_gate", "sealed_gate", "old_capital_outer_wall"],
                        }
                    },
                    "travel_cost": 1.0,
                }
            )

        if has_road:
            terrain_type = "ruin_road_main" if terrain_type == "city_ruins" else terrain_type
            tags.extend(["road", "ancient_highway"])
            flags["has_road"] = True
            flags["route"] = {
                "type": "ancient_highway",
                "role": "hub_to_outer_gate",
                "tags": ["road", "ancient_highway", "main_route"],
            }

        influence = ThreatService.describe(x, y)
        flags["anchor_influence"] = {
            "threat": influence.threat,
            "tier": influence.tier,
            "dominant_anchor": influence.dominant_anchor,
            "tags": influence.tags,
            "is_inside_city_shield": influence.is_inside_city_shield,
        }
        flags["world_theme"] = WorldThemeService.build(x, y, loc_id=f"{x}_{y}").model_dump(mode="json")

        return {
            "x": x,
            "y": y,
            "zone_id": zone_id,
            "terrain_type": terrain_type,
            "services": [],
            "content": {
                "title": title,
                "description": description,
                "environment_tags": list(dict.fromkeys(tags)),
            },
            "is_active": True,
            "flags": flags,
        }

    async def _enrich_d4_capital_nodes_with_ai(self) -> None:
        """Generate D4 node titles/descriptions using the legacy tag batch contract."""
        if not self.ai:
            return

        min_x = (4 - 1) * REGION_SIZE
        min_y = REGION_ROWS.index("D") * REGION_SIZE
        nodes = await self.data.get_nodes_in_rect(min_x - 1, min_y - 1, REGION_SIZE + 2, REGION_SIZE + 2)
        node_map = {(node.x, node.y): node for node in nodes}
        payload_items = []
        static_coords = set(STATIC_LOCATIONS)

        for x in range(min_x, min_x + REGION_SIZE):
            for y in range(min_y, min_y + REGION_SIZE):
                if (x, y) in static_coords:
                    continue

                node = node_map.get((x, y))
                if node is None:
                    continue

                tags = self._collect_location_tags(
                    x=x,
                    y=y,
                    node=node,
                    chunk_start_x=min_x,
                    chunk_start_y=min_y,
                )
                context = self._scan_d4_surroundings(x, y, node_map)
                payload_items.append(
                    {
                        "id": f"{x}_{y}",
                        "tags": tags,
                        "context": context,
                        "route_context": self._build_route_context(node),
                        "boundary_context": self._build_boundary_context(node),
                    }
                )

        for batch in self._chunks(payload_items, D4_CONTENT_BATCH_SIZE):
            result_map = await self._request_location_batch_with_retries(batch)
            if not result_map:
                await self._mark_location_batch_ai_status(batch, "fallback")
                continue

            result_map = self._filter_complete_location_batch(result_map, batch)
            if not result_map:
                await self._mark_location_batch_ai_status(batch, "fallback")
                continue

            await self._save_location_batch_content(batch, result_map)

    async def _request_location_batch_with_retries(self, batch: list[dict[str, Any]]) -> dict[str, Any] | None:
        for attempt, delay in enumerate((*D4_CONTENT_RETRY_DELAYS_SECONDS, 0.0), start=1):
            try:
                assert self.ai is not None
                raw_response = await self.ai.process("batch_location_desc", payload_items=batch)
            except Exception as exc:
                log.warning(
                    "World AI location batch failed; attempt=%d/%d first_id=%s error=%s",
                    attempt,
                    len(D4_CONTENT_RETRY_DELAYS_SECONDS) + 1,
                    batch[0]["id"] if batch else "<empty>",
                    exc,
                )
                if delay:
                    await asyncio.sleep(delay)
                continue

            result_map = self._parse_ai_json_map(raw_response)
            if not result_map:
                log.warning(
                    "World AI location batch returned invalid JSON; attempt=%d/%d first_id=%s",
                    attempt,
                    len(D4_CONTENT_RETRY_DELAYS_SECONDS) + 1,
                    batch[0]["id"] if batch else "<empty>",
                )
                if delay:
                    await asyncio.sleep(delay)
                continue
            return result_map

        return None

    async def _save_location_batch_content(self, batch: list[dict[str, Any]], result_map: dict[str, Any]) -> None:
        for loc_id, text_data in result_map.items():
            try:
                x, y = map(int, loc_id.split("_"))
            except ValueError:
                continue

            original_item = next((item for item in batch if item["id"] == loc_id), None)
            if original_item is None or not isinstance(text_data, dict):
                continue

            await self.data.update_content(
                x,
                y,
                {
                    "title": text_data.get("title") or "Руины Старой Столицы",
                    "description": text_data.get("description") or "...",
                    "environment_tags": original_item["tags"],
                },
            )

    async def _mark_location_batch_ai_status(self, batch: list[dict[str, Any]], status: str) -> None:
        for item in batch:
            try:
                x, y = map(int, item["id"].split("_"))
            except (KeyError, ValueError):
                continue
            await self.data.update_flags(x, y, {"ai_content_status": status})

    @staticmethod
    def _filter_complete_location_batch(
        result_map: dict[str, Any], batch: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        expected_ids = {item["id"] for item in batch}
        actual_ids = set(result_map)
        missing_ids = expected_ids - actual_ids
        extra_ids = actual_ids - expected_ids

        if missing_ids:
            log.warning("World AI location batch missing ids: %s", sorted(missing_ids))
            return None
        if extra_ids:
            log.warning("World AI location batch returned extra ids: %s", sorted(extra_ids))

        filtered = {loc_id: result_map[loc_id] for loc_id in expected_ids if isinstance(result_map.get(loc_id), dict)}
        invalid_ids = expected_ids - set(filtered)
        if invalid_ids:
            log.warning("World AI location batch returned invalid entries: %s", sorted(invalid_ids))
            return None
        return filtered

    def _collect_location_tags(self, *, x: int, y: int, node: Any, chunk_start_x: int, chunk_start_y: int) -> list[str]:
        content = node.content if isinstance(node.content, dict) else {}
        base_tags = list(content.get("environment_tags") or [])
        structural_tags = self._get_structural_tags(
            x=x,
            y=y,
            start_x=chunk_start_x,
            start_y=chunk_start_y,
            chunk_size=REGION_SIZE,
            main_biome="city_ruins",
        )
        influence_tags = ThreatService.get_narrative_tags(x, y)
        flags = node.flags if isinstance(node.flags, dict) else {}
        road_tags = ["road"] if flags.get("has_road") else []
        route = flags.get("route", {})
        route_tags = route.get("tags", []) if isinstance(route, dict) else []
        boundary_tags = []
        boundary_features = flags.get("boundary_features", {})
        if isinstance(boundary_features, dict):
            for feature in boundary_features.values():
                if isinstance(feature, dict):
                    boundary_tags.extend(feature.get("tags", []))
        return list(
            dict.fromkeys([*base_tags, *structural_tags, *influence_tags, *road_tags, *route_tags, *boundary_tags])
        )

    @staticmethod
    def _build_route_context(node: Any) -> dict[str, Any] | None:
        flags = node.flags if isinstance(node.flags, dict) else {}
        route = flags.get("route")
        if not isinstance(route, dict):
            return None
        return {
            "type": route.get("type"),
            "role": route.get("role"),
            "tags": route.get("tags", []),
            "must_describe": True,
        }

    @staticmethod
    def _build_boundary_context(node: Any) -> dict[str, Any]:
        flags = node.flags if isinstance(node.flags, dict) else {}
        boundary_features = flags.get("boundary_features", {})
        return boundary_features if isinstance(boundary_features, dict) else {}

    @staticmethod
    def _get_structural_tags(
        *, x: int, y: int, start_x: int, start_y: int, chunk_size: int, main_biome: str
    ) -> list[str]:
        local_x = x - start_x
        local_y = y - start_y
        center = chunk_size // 2
        is_edge = local_x == 0 or local_x == chunk_size - 1 or local_y == 0 or local_y == chunk_size - 1
        if local_x == center and local_y == center:
            return [f"{main_biome}_center"]
        if is_edge:
            return [f"{main_biome}_edge"]
        return [f"deep_{main_biome}"]

    @staticmethod
    def _scan_d4_surroundings(x: int, y: int, node_map: dict[tuple[int, int], Any]) -> list[str]:
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
        visual_tags = {
            "gate",
            "bastion",
            "portal",
            "wall",
            "ruins",
            "ancient_highway",
            "monolithic_wall",
            "locked_exit",
            "safe_zone",
        }
        for dx, dy, side_name in directions:
            neighbor = node_map.get((x + dx, y + dy))
            if neighbor is None:
                continue

            content = neighbor.content if isinstance(neighbor.content, dict) else {}
            tags = content.get("environment_tags") or []
            for tag in tags:
                if tag in visual_tags:
                    hints.append(f"На {side_name} виднеется {tag}")
                    break

        if abs(x - HUB_CENTER["x"]) <= 7 and abs(y - HUB_CENTER["y"]) <= 7:
            hints.append("Неподалеку виднеется Шпиль Хаба.")
        return list(dict.fromkeys(hints))

    @staticmethod
    def _parse_ai_json_map(raw_response: Any) -> dict[str, Any] | None:
        if isinstance(raw_response, dict):
            return raw_response
        if not isinstance(raw_response, str):
            return None

        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
        if not clean_json:
            return None
        try:
            parsed = json.loads(clean_json)
        except json.JSONDecodeError:
            log.warning("World AI content response is not valid JSON")
            return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _chunks(items: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
        for i in range(0, len(items), size):
            yield items[i : i + size]

    @staticmethod
    def _build_d4_road_cells(*, min_x: int, min_y: int, max_x: int, max_y: int) -> set[tuple[int, int]]:
        hub_x = HUB_CENTER["x"]
        hub_y = HUB_CENTER["y"]
        return {
            *((x, hub_y) for x in range(min_x, max_x + 1)),
            *((hub_x, y) for y in range(min_y, max_y + 1)),
        }

    @staticmethod
    def _is_d4_hub_node(x: int, y: int) -> bool:
        return 50 <= x <= 54 and 50 <= y <= 54

    @staticmethod
    def _d4_gate_direction(*, x: int, y: int, min_x: int, min_y: int, max_x: int, max_y: int) -> str:
        if y == min_y:
            return "north"
        if y == max_y:
            return "south"
        if x == min_x:
            return "west"
        if x == max_x:
            return "east"
        raise ValueError(f"D4 gate coordinate is not on boundary: {x}_{y}")

    @staticmethod
    def _ru_direction(direction: str) -> str:
        return {"north": "Северные", "south": "Южные", "west": "Западные", "east": "Восточные"}[direction]

    @staticmethod
    def _d4_boundary_blocked_exits(*, x: int, y: int, min_x: int, min_y: int, max_x: int, max_y: int) -> list[str]:
        blocked = []
        if y == min_y:
            blocked.append("north")
        if y == max_y:
            blocked.append("south")
        if x == min_x:
            blocked.append("west")
        if x == max_x:
            blocked.append("east")
        return blocked

    @staticmethod
    def _d4_boundary_features(
        directions: list[str], *, kind: str, state: str, tags: list[str]
    ) -> dict[str, dict[str, Any]]:
        return {direction: {"kind": kind, "state": state, "tags": tags} for direction in directions}

    async def _generate_world_shell(self) -> None:
        """Generates the skeleton of regions and zones using anchor influence."""
        for r_idx, row_char in enumerate(REGION_ROWS):
            for col_idx in range(1, len(REGION_ROWS) + 1):
                region_id = f"{row_char}{col_idx}"
                region_influence = ThreatService.describe(
                    (col_idx - 1) * REGION_SIZE + REGION_SIZE // 2,
                    r_idx * REGION_SIZE + REGION_SIZE // 2,
                )
                region_tags = [
                    "ancient_world",
                    region_influence.biome_id,
                    *region_influence.tags,
                ]
                await self.data.upsert_region(region_id, climate_tags=list(dict.fromkeys(region_tags)))

                # Create 3x3 zones per region (simplified)
                zones_per_region = REGION_SIZE // ZONE_SIZE
                for zx in range(zones_per_region):
                    for zy in range(zones_per_region):
                        zone_id = f"{region_id}_{zx}_{zy}"
                        center_x = (col_idx - 1) * REGION_SIZE + zx * ZONE_SIZE + ZONE_SIZE // 2
                        center_y = r_idx * REGION_SIZE + zy * ZONE_SIZE + ZONE_SIZE // 2
                        influence = ThreatService.describe(center_x, center_y)
                        world_theme = WorldThemeService.build(center_x, center_y, loc_id=zone_id)

                        await self.data.upsert_zone(
                            zone_id,
                            region_id=region_id,
                            biome_id=influence.biome_id,
                            tier=influence.tier,
                            flags={
                                "is_safe_zone": False,
                                "threat": influence.threat,
                                "threat_tier": influence.tier,
                                "dominant_anchor": influence.dominant_anchor,
                                "anchor_tags": influence.tags,
                                "is_inside_city_shield": influence.is_inside_city_shield,
                                "world_theme": world_theme.model_dump(mode="json"),
                            },
                        )
        log.info("World shell (regions/zones) generated.")

    async def _enrich_zone_with_ai(self, zone_id: str) -> None:
        """Uses LLM to enrich zone lore and node descriptions."""
        zone = await self.data.get_zone(zone_id)
        if not zone or not self.ai:
            return

        log.info("Enriching zone %s with AI lore...", zone_id)
        for attempt, delay in enumerate((*ZONE_LORE_RETRY_DELAYS_SECONDS, 0.0), start=1):
            try:
                lore_raw = await self.ai.process(
                    "zone_lore", region_id=zone.region_id, biome_id=zone.biome_id, tier=zone.tier
                )
            except Exception as exc:
                log.warning(
                    "Zone lore AI request failed; zone=%s attempt=%d/%d error=%s",
                    zone_id,
                    attempt,
                    len(ZONE_LORE_RETRY_DELAYS_SECONDS) + 1,
                    exc,
                )
                if delay:
                    await asyncio.sleep(delay)
                continue

            lore = self._parse_ai_json_map(lore_raw)
            if not lore:
                log.warning(
                    "Zone lore AI response is empty or invalid JSON; zone=%s attempt=%d/%d",
                    zone_id,
                    attempt,
                    len(ZONE_LORE_RETRY_DELAYS_SECONDS) + 1,
                )
                if delay:
                    await asyncio.sleep(delay)
                continue

            lore_name = lore.get("name", zone.id)
            lore_background = lore.get("background", "")
            await self.data.save_zone_lore(zone, lore_name=lore_name, lore_background=lore_background)
            log.info("AI Lore generated for %s: %s", zone_id, lore_name)
            return

        log.warning("Zone lore AI enrichment skipped after retries; zone=%s", zone_id)

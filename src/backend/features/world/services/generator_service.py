import json
import logging

from src.backend.core.ai import AIService
from src.backend.config.settings import settings
from src.backend.features.world.loaders.village_loader import VillageLoader
from src.backend.features.world.prompts.router import world_prompt_router
from src.backend.infrastructure.world.models import WorldRegion, WorldZone
from src.backend.infrastructure.world.repositories import WorldRepository

log = logging.getLogger(__name__)


class LLMWorldGenerator:
    """Orchestrates world generation using static loaders and AI-driven content."""

    def __init__(self, repository: WorldRepository, ai: AIService) -> None:
        self.repository = repository
        self.village_loader = VillageLoader(repository)
        self.ai = ai
        
        # Register world-specific prompts
        self.ai.include_router(world_prompt_router)

    async def run(self, mode: str = "test") -> None:
        """Runs the generation process.

        1. Load static village.
        2. Generate surrounding regions and zones.
        3. Populate with AI content if enabled.
        """
        log.info("Starting world generation (mode=%s)", mode)

        # 1. Load Starting Village (D4)
        import importlib.util
        from pathlib import Path

        temp_path = Path("temp/backend/resources/game_data/graf_data_world/start_vilage.py")
        if temp_path.exists():
            spec = importlib.util.spec_from_file_location("temp_village", str(temp_path.resolve()))
            if spec and spec.loader:
                temp_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(temp_module)
                static_locations = getattr(temp_module, "STATIC_LOCATIONS", {})
                await self.village_loader.load_village(static_locations)

        # 2. Generate Shell (Regions/Zones)
        if mode == "full":
            await self._generate_world_shell()

        # 3. AI Enrichment (Example for Hub Zone)
        if self.ai and mode != "test":
            await self._enrich_zone_with_ai("D4_hub")

    async def _generate_world_shell(self) -> None:
        """Generates the skeleton of regions and zones (8x8 regions)."""
        rows = "ABCDEFGH"
        for r_idx, row_char in enumerate(rows):
            for col_idx in range(1, 9):
                region_id = f"{row_char}{col_idx}"
                await self.repository.upsert_region(WorldRegion(id=region_id, climate_tags=[]))

                # Create 3x3 zones per region (simplified)
                for zx in range(3):
                    for zy in range(3):
                        zone_id = f"{region_id}_{zx}_{zy}"
                        if zone_id == "D4_hub":  # Skip already handled village
                            continue

                        # Basic biome heuristic
                        biome_id = "wilderness"
                        tier = max(1, abs(r_idx - 3) + abs(col_idx - 4))

                        await self.repository.upsert_zone(
                            WorldZone(
                                id=zone_id,
                                region_id=region_id,
                                biome_id=biome_id,
                                tier=tier,
                                flags={"is_safe_zone": False}
                            )
                        )
        log.info("World shell (regions/zones) generated.")

    async def _enrich_zone_with_ai(self, zone_id: str) -> None:
        """Uses LLM to enrich zone lore and node descriptions."""
        zone = await self.repository.get_zone(zone_id)
        if not zone or not self.ai:
            return

        log.info("Enriching zone %s with AI lore...", zone_id)
        try:
            lore_json = await self.ai.process(
                "zone_lore",
                region_id=zone.region_id,
                biome_id=zone.biome_id,
                tier=zone.tier
            )
            lore = json.loads(lore_json)
            zone.name = lore.get("name", zone.id)
            zone.flags["lore_background"] = lore.get("background", "")
            await self.repository.upsert_zone(zone)
            log.info("AI Lore generated for %s: %s", zone_id, zone.name)
        except Exception as e:
            log.error("Failed to enrich zone with AI: %s", e)

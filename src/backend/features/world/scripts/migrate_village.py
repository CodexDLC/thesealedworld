import asyncio
import importlib.util
import logging
import sys
from pathlib import Path

from src.backend.core.database import get_session_context
from src.backend.infrastructure.world.repositories import WorldRepository
from src.backend.features.world.loaders.village_loader import VillageLoader

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

async def run_migration():
    # 1. Path to the temp village data
    temp_village_path = Path("temp/backend/resources/game_data/graf_data_world/start_vilage.py").resolve()
    
    if not temp_village_path.exists():
        log.error("Village data not found at %s", temp_village_path)
        return

    # 2. Dynamic import
    spec = importlib.util.spec_from_file_location("temp_village", str(temp_village_path))
    if not spec or not spec.loader:
        log.error("Could not load module spec for %s", temp_village_path)
        return
        
    temp_village = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(temp_village)
    
    static_locations = getattr(temp_village, "STATIC_LOCATIONS", None)
    if not static_locations:
        log.error("STATIC_LOCATIONS not found in %s", temp_village_path)
        return

    # 3. Perform migration
    log.info("Starting village migration...")
    async with get_session_context() as session:
        repository = WorldRepository(session)
        loader = VillageLoader(repository)
        
        count = await loader.load_village(static_locations)
        await session.commit()
        
    log.info("Migration finished. Total nodes migrated: %d", count)

if __name__ == "__main__":
    asyncio.run(run_migration())

import asyncio
import logging

from src.backend.core.database import get_session_context
from src.backend.features.world.integrations import WorldDataIntegration
from src.backend.features.world.loaders.village_loader import VillageLoader
from src.backend.features.world.resources.static.start_village import STATIC_LOCATIONS
from src.backend.infrastructure.world.repositories import WorldRepository

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def run_migration():
    log.info("Starting village migration...")
    async with get_session_context() as session:
        data = WorldDataIntegration(WorldRepository(session))
        loader = VillageLoader(data)

        count = await loader.load_village(STATIC_LOCATIONS)
        await session.commit()

    log.info("Migration finished. Total nodes migrated: %d", count)


if __name__ == "__main__":
    asyncio.run(run_migration())

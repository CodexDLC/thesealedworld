import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.backend.features.scenario.loaders.scenario_loader import ScenarioLoader
from src.backend.core.database import async_session_factory as session_maker
from src.backend.config.settings import settings

async def reload_quest():
    print("Initializing database session...")
    # Use the imported session_maker (async_session_factory)
    async with session_maker() as session:
        loader = ScenarioLoader(session)
        quest_path = Path("src/backend/features/scenario/resources/json/awakening_rift")

        print(f"Loading quest from {quest_path}...")
        quest_key = await loader.load_from_file(quest_path)
        print(f"Successfully reloaded quest: {quest_key}")

if __name__ == "__main__":
    asyncio.run(reload_quest())

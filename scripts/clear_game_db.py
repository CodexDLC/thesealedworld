import asyncio
import sys
from pathlib import Path

import redis
from pymongo import MongoClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.backend.config.settings import settings  # noqa: E402


async def clear_postgres():
    print(f"🧹 Clearing PostgreSQL game database: {settings.game_database_url}")
    engine = create_async_engine(settings.game_database_url)
    async with engine.begin() as conn:
        print("Dropping schema chat cascade...")
        await conn.execute(text("DROP SCHEMA IF EXISTS chat CASCADE"))
        print("Dropping schema public cascade...")
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        print("Re-creating schema public...")
        await conn.execute(text("CREATE SCHEMA public"))
        print("Granting permissions on schema public...")
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO tbmmorpg"))
    await engine.dispose()
    print("✅ PostgreSQL cleared!")


def clear_mongo():
    print(f"🍃 Clearing MongoDB database: {settings.mongo_database} ({settings.mongo_url})")
    client = MongoClient(settings.mongo_url)
    client.drop_database(settings.mongo_database)
    client.close()
    print("✅ MongoDB cleared!")


def clear_redis():
    # Force use the docker mapped port 6380 on the host
    url = "redis://:dev_redis_password@127.0.0.1:6380/0"
    print(f"🔴 Clearing Redis: {url}")
    r = redis.from_url(url)
    r.flushall()
    print("✅ Redis cleared!")


async def main():
    print("=== STARTING FULL CLEAN UP ===")
    await clear_postgres()
    clear_mongo()
    clear_redis()
    print("=== FULL CLEAN UP COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    asyncio.run(main())

import sys
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.backend.config.settings import settings  # noqa: E402


def runserver():
    """Run the FastAPI backend server."""
    print(f"🎮 Starting backend server at http://{settings.app_host}:{settings.app_port}")
    uvicorn.run(
        "src.backend.app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="info",
    )


def run_migrations():
    """Apply migrations to the database."""
    print("🚀 Running database migrations...")
    alembic_cfg = Config(PROJECT_ROOT / "src/backend/alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("✅ Migrations applied!")


def make_migration(message: str = "auto"):
    """Create a new migration revision."""
    print(f"📝 Creating new migration: {message}")
    alembic_cfg = Config(PROJECT_ROOT / "src/backend/alembic.ini")
    command.revision(alembic_cfg, message=message, autogenerate=True)
    print("✅ Migration created!")


async def bootstrap_data():
    """Load initial scenario data into the database."""
    from src.backend.core.bootstrap import bootstrap_scenarios

    print("📦 Bootstrapping scenario data...")
    await bootstrap_scenarios()
    print("✅ Data loaded!")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or "runserver" in args:
        runserver()
    elif "upgrade" in args:
        run_migrations()
    elif "migrate" in args:
        msg = args[1] if len(args) > 1 else "manual_update"
        make_migration(msg)
    elif "bootstrap" in args:
        import asyncio

        asyncio.run(bootstrap_data())
    elif "prepare" in args:
        # Run everything for setup
        import asyncio

        run_migrations()
        asyncio.run(bootstrap_data())
    else:
        print("Unknown command. Available: runserver, upgrade, migrate, bootstrap, prepare")

import sys
from pathlib import Path

import uvicorn

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.backend.config.settings import settings


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


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or "runserver" in args:
        runserver()
    else:
        print("Unknown command. Available: runserver")

import sys
from pathlib import Path

import uvicorn

# Add project root to path so we can import src
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.frontend.config.settings import settings


def runserver():
    """Run the FastAPI development server."""
    print(f"🚀 Starting frontend server at http://{settings.app_host}:{settings.app_port}")
    uvicorn.run(
        "src.frontend.app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,  # Auto-reload if debug is True
        log_level="info",
    )


def compile_static():
    """Manually trigger static assets compilation."""
    from src.frontend.core.static import compile_static_assets

    print("🎨 Compiling static assets...")
    compile_static_assets(minify=not settings.debug)
    print("✅ Done!")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or "runserver" in args:
        runserver()
    elif "compile" in args:
        compile_static()
    else:
        print("Unknown command. Available: runserver, compile")

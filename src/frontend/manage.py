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


async def create_superuser(email: str, password: str) -> None:
    """Create a new superuser or promote an existing user to superuser."""
    from src.frontend.core.database.session import create_db_tables, get_session_context
    from src.frontend.features.auth.repositories.user_repository import UserRepository
    from src.frontend.features.auth.security.passwords import get_password_hash

    await create_db_tables()

    async with get_session_context() as session:
        repo = UserRepository(session)
        user = await repo.get_by_email(email)
        if user is not None:
            user.is_superuser = True
            print(f"✅ Promoted existing user to superuser: {email}")
        else:
            from src.frontend.features.auth.models import User

            new_user = User(
                email=email,
                hashed_password=get_password_hash(password),
                is_active=True,
                is_superuser=True,
            )
            session.add(new_user)
            print(f"✅ Created superuser: {email}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or "runserver" in args:
        runserver()
    elif "compile" in args:
        compile_static()
    elif "createsuperuser" in args:
        import asyncio
        import getpass

        idx = args.index("createsuperuser")
        email_arg = args[idx + 1] if len(args) > idx + 1 else input("Email: ")
        password_arg = args[idx + 2] if len(args) > idx + 2 else getpass.getpass("Password: ")
        asyncio.run(create_superuser(email_arg, password_arg))
    else:
        print("Unknown command. Available: runserver, compile, createsuperuser <email> [password]")

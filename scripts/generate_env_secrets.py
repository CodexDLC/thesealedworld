from __future__ import annotations

import secrets
import string
from urllib.parse import quote


def token_urlsafe(nbytes: int = 48) -> str:
    return secrets.token_urlsafe(nbytes)


def password(length: int = 40) -> str:
    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> None:
    internal_service_key = token_urlsafe()
    postgres_user = "tbmmorpg"
    postgres_password = password()
    postgres_password_quoted = quote(postgres_password, safe="")
    redis_password = password()
    redis_password_quoted = quote(redis_password, safe="")

    values = {
        "SECRET_KEY": token_urlsafe(64),
        "POSTGRES_USER": postgres_user,
        "POSTGRES_PASSWORD": postgres_password,
        "POSTGRES_DB": "tbmmorpg_site",
        "SITE_DATABASE_URL": (
            f"postgresql+asyncpg://{postgres_user}:{postgres_password_quoted}@postgres:5432/tbmmorpg_site"
        ),
        "GAME_DATABASE_URL": (
            f"postgresql+asyncpg://{postgres_user}:{postgres_password_quoted}@postgres:5432/tbmmorpg_game"
        ),
        "REDIS_PASSWORD": redis_password,
        "REDIS_URL": f"redis://:{redis_password_quoted}@redis:6379/0",
        "SITE_TO_GAME_SERVICE_KEY": token_urlsafe(),
        "FRONTEND_INTERNAL_SERVICE_KEY": internal_service_key,
        "BACKEND_INTERNAL_SERVICE_KEY": internal_service_key,
    }

    print("# Generated production env secrets")
    print("# Copy these into .env.prod or into the GitHub ENV_FILE secret.")
    print("# Provider, SMTP, domain, and Docker image values are not generated here.")
    for key, value in values.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()

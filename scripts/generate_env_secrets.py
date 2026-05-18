from __future__ import annotations

import secrets
import string


def token_urlsafe(nbytes: int = 48) -> str:
    return secrets.token_urlsafe(nbytes)


def password(length: int = 40) -> str:
    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> None:
    internal_service_key = token_urlsafe()
    values = {
        "SECRET_KEY": token_urlsafe(64),
        "POSTGRES_PASSWORD": password(),
        "REDIS_PASSWORD": password(),
        "SITE_TO_GAME_SERVICE_KEY": token_urlsafe(),
        "FRONTEND_INTERNAL_SERVICE_KEY": internal_service_key,
        "BACKEND_INTERNAL_SERVICE_KEY": internal_service_key,
    }

    print("# Generated production env secrets")
    print("# Copy these into .env.prod or into the GitHub ENV_FILE secret.")
    print("# API provider keys are not generated here; copy them as-is.")
    for key, value in values.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()

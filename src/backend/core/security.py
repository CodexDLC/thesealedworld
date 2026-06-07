from datetime import timedelta
from typing import Any

from authx import AuthX, AuthXConfig, RequestToken
from authx.exceptions import JWTDecodeError, TokenExpiredError, TokenInvalidSignatureError

from src.backend.config.settings import settings
from src.shared.security.passwords import (
    PASSWORD_ITERATIONS,
    get_password_hash,
    verify_password,
)

ALGORITHM = "HS256"
authx: AuthX = AuthX(
    config=AuthXConfig(
        JWT_SECRET_KEY=settings.secret_key,
        JWT_ALGORITHM=settings.authx_jwt_algorithm,  # type: ignore[arg-type]
        JWT_TOKEN_LOCATION=settings.authx_jwt_token_locations,  # type: ignore[arg-type]
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=settings.access_token_expire_minutes),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=settings.refresh_token_expire_days),
    )
)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    return authx.create_access_token(
        uid=str(subject),
        expiry=expires_delta or timedelta(minutes=settings.access_token_expire_minutes),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    request_token = RequestToken(token=token, type="access", location="headers")
    try:
        payload = authx.verify_token(request_token, verify_type=True, verify_csrf=False)
    except TokenExpiredError as exc:
        raise ValueError("Token expired") from exc
    except TokenInvalidSignatureError as exc:
        raise ValueError("Invalid token signature") from exc
    except JWTDecodeError as exc:
        message = str(exc)
        if "expired" in message.lower():
            raise ValueError("Token expired") from exc
        if "signature" in message.lower():
            raise ValueError("Invalid token signature") from exc
        raise ValueError("Invalid token") from exc
    return payload.model_dump()


__all__ = [
    "ALGORITHM",
    "PASSWORD_ITERATIONS",
    "authx",
    "create_access_token",
    "decode_access_token",
    "get_password_hash",
    "verify_password",
]

from datetime import timedelta
from typing import Any

from authx import RequestToken
from authx.exceptions import JWTDecodeError, TokenExpiredError, TokenInvalidSignatureError

from src.backend.config.settings import settings
from src.backend.features_site.auth.security.authx_runtime import authx


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

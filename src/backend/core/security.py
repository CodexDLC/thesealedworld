import base64
import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any

from authx import AuthX, AuthXConfig, RequestToken
from authx.exceptions import JWTDecodeError, TokenExpiredError, TokenInvalidSignatureError

from src.backend.config.settings import settings

ALGORITHM = "HS256"
PASSWORD_ITERATIONS = 390_000
authx: AuthX = AuthX(
    config=AuthXConfig(
        JWT_SECRET_KEY=settings.secret_key,
        JWT_ALGORITHM=settings.authx_jwt_algorithm,  # type: ignore[arg-type]
        JWT_TOKEN_LOCATION=settings.authx_jwt_token_locations,  # type: ignore[arg-type]
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=settings.access_token_expire_minutes),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=settings.refresh_token_expire_days),
    )
)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


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


def get_password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        scheme, iterations_raw, salt_raw, digest_raw = hashed_password.split("$", maxsplit=3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = _b64url_decode(salt_raw)
        expected = _b64url_decode(digest_raw)
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)

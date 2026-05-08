import base64
import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any

from src.backend.features_site.auth.security.token_service import (
    create_access_token as _create_access_token,
)
from src.backend.features_site.auth.security.token_service import (
    decode_access_token as _decode_access_token,
)

ALGORITHM = "HS256"
PASSWORD_ITERATIONS = 390_000


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    return _create_access_token(subject, expires_delta=expires_delta)


def decode_access_token(token: str) -> dict[str, Any]:
    return _decode_access_token(token)


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

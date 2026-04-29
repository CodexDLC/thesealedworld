import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from src.backend.config.settings import settings

ALGORITHM = "HS256"
PASSWORD_ITERATIONS = 390_000


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = {"exp": int(expire.timestamp()), "sub": str(subject)}

    header_part = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(settings.secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_part}.{payload_part}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    header_part, payload_part, signature_part = token.split(".")
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    expected = hmac.new(settings.secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual = _b64url_decode(signature_part)
    if not hmac.compare_digest(expected, actual):
        raise ValueError("Invalid token signature")

    payload = json.loads(_b64url_decode(payload_part))
    exp = payload.get("exp")
    if not isinstance(exp, int) or datetime.now(UTC).timestamp() >= exp:
        raise ValueError("Token expired")
    return payload


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

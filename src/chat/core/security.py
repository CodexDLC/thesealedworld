import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from src.chat.config import settings

ALGORITHM = "HS256"


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_part, payload_part, signature_part = token.split(".")
    except ValueError:
        raise ValueError("Malformed token") from None

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

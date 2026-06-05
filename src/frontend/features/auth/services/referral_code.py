import secrets

# Crockford-ish alphabet without 0/O/1/I/L for visual unambiguity in printed codes.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # pragma: allowlist secret
_PREFIX = "SEAL-"
_BODY_LENGTH = 8


def generate_referral_code() -> str:
    return _PREFIX + "".join(secrets.choice(_ALPHABET) for _ in range(_BODY_LENGTH))


def normalize_referral_code(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = raw.strip().upper()
    if not cleaned:
        return None
    if not cleaned.startswith(_PREFIX):
        return None
    return cleaned

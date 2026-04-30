import pytest
from datetime import timedelta, datetime, UTC
import time
from src.backend.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password
)

@pytest.mark.unit
class TestSecurity:
    def test_token_encode_decode(self):
        subject = "user123"
        token = create_access_token(subject, expires_delta=timedelta(minutes=5))
        payload = decode_access_token(token)
        assert payload["sub"] == subject
        assert "exp" in payload

    def test_decode_invalid_token_signature(self):
        token = create_access_token("sub")
        parts = token.split(".")
        # Corrupt the signature part
        parts[2] = "invalid_sig"
        corrupted_token = ".".join(parts)

        with pytest.raises(ValueError, match="Invalid token signature"):
            decode_access_token(corrupted_token)

    def test_decode_expired_token(self):
        # Create a token that expires in the past
        token = create_access_token("sub", expires_delta=timedelta(seconds=-10))

        with pytest.raises(ValueError, match="Token expired"):
            decode_access_token(token)

    def test_password_hashing(self):
        password = "secret_password"  # pragma: allowlist secret
        hashed = get_password_hash(password)
        assert hashed.startswith("pbkdf2_sha256$")
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_verify_invalid_hash_format(self):
        assert verify_password("pass", "invalid_format") is False
        assert verify_password("pass", "wrong_scheme$123$salt$digest") is False

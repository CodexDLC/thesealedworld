import pytest

from src.frontend.features.auth.services.referral_code import (
    generate_referral_code,
    normalize_referral_code,
)


@pytest.mark.unit
def test_generate_referral_code_has_seal_prefix_and_alphabet():
    code = generate_referral_code()
    assert code.startswith("SEAL-")
    body = code.removeprefix("SEAL-")
    assert len(body) == 8
    allowed = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
    assert set(body).issubset(allowed)


@pytest.mark.unit
def test_generate_referral_code_is_random():
    codes = {generate_referral_code() for _ in range(50)}
    assert len(codes) == 50


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("seal-abcd1234", "SEAL-ABCD1234"),
        ("  SEAL-XYZ  ", "SEAL-XYZ"),
        ("", None),
        (None, None),
        ("plain-code", None),
        ("seal-", "SEAL-"),
    ],
)
def test_normalize_referral_code(raw, expected):
    assert normalize_referral_code(raw) == expected

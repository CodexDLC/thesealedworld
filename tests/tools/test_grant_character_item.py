from __future__ import annotations

import argparse

import pytest
from tools.grant_character_item import build_source_context, parse_positive_int


def test_build_source_context_includes_monster_family_alias_and_member_data() -> None:
    args = argparse.Namespace(
        monster_family_id="bandit_gang",
        member_role="bandit",
        member_tier=2,
    )

    assert build_source_context(args) == {
        "monster_family_id": "bandit_gang",
        "family_id": "bandit_gang",
        "member_role": "bandit",
        "member_tier": 2,
    }


def test_build_source_context_omits_empty_values() -> None:
    args = argparse.Namespace(
        monster_family_id=None,
        member_role=None,
        member_tier=None,
    )

    assert build_source_context(args) == {}


def test_parse_positive_int_rejects_zero() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="must be >= 1"):
        parse_positive_int("0")


def test_parse_positive_int_accepts_positive_value() -> None:
    assert parse_positive_int("2") == 2

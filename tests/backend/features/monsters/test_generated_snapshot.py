from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from src.backend.features.monsters.scripts.generated_snapshot import _decode_payload, _encode_value, _same_payload


def test_generated_snapshot_comparison_ignores_runtime_timestamps() -> None:
    left = {
        "identity_hash": "same",
        "title": "Generated Clan",
        "created_at": datetime(2026, 6, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 2, tzinfo=UTC),
    }
    right = {
        "identity_hash": "same",
        "title": "Generated Clan",
        "created_at": datetime(2026, 6, 3, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 4, tzinfo=UTC),
    }

    assert _same_payload(left, right)


def test_generated_snapshot_comparison_detects_content_drift() -> None:
    left = {"identity_hash": "same", "title": "Generated Clan"}
    right = {"identity_hash": "same", "title": "Changed Clan"}

    assert not _same_payload(left, right)


def test_generated_snapshot_round_trips_uuid_and_datetime() -> None:
    payload = {
        "id": UUID("1cd9f702-2f3b-44a0-a865-afbf76a7936c"),
        "created_at": datetime(2026, 6, 5, 7, 0, tzinfo=UTC),
    }

    assert _decode_payload(_encode_value(payload)) == payload

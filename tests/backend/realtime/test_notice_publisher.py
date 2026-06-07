from __future__ import annotations

import json
from typing import Any

import pytest

from src.backend.realtime.integrations.notice_publisher import (
    PLAYER_NOTICE_EVENT,
    NoticeTemplates,
    PlayerNoticePublisher,
    RawStreamNoticeProducer,
    RefreshTargets,
    build_player_notice_payload,
)


class FakeProducer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        self.calls.append((event_type, data))


@pytest.mark.unit
def test_build_payload_is_flat_and_json_encoded() -> None:
    payload = build_player_notice_payload(
        character_ids=[42, 7],
        template_key=NoticeTemplates.SAFE_ZONE_ENTERED,
        variables={"location": "Площадь рун"},
        domain="exploration",
    )

    assert payload["character_ids"] == "[42, 7]"
    assert json.loads(payload["character_ids"]) == [42, 7]
    assert payload["variables"] == json.dumps({"location": "Площадь рун"}, default=str)
    assert payload["template_key"] == "exploration.safe_zone_entered"
    assert payload["presentation"] == "system_chat"
    assert payload["severity"] == "info"
    assert payload["domain"] == "exploration"
    # every value is a primitive string-safe scalar
    assert all(isinstance(v, str) for v in payload.values())


@pytest.mark.unit
async def test_player_died_publishes_player_notice() -> None:
    producer = FakeProducer()
    await PlayerNoticePublisher(producer).player_died(42)

    assert len(producer.calls) == 1
    event, data = producer.calls[0]
    assert event == PLAYER_NOTICE_EVENT
    assert data["template_key"] == NoticeTemplates.PLAYER_DEATH
    assert data["severity"] == "danger"
    assert json.loads(data["character_ids"]) == [42]
    assert json.loads(data["variables"]) == {}


@pytest.mark.unit
async def test_safe_zone_entered_carries_location_variable() -> None:
    producer = FakeProducer()
    await PlayerNoticePublisher(producer).safe_zone_entered(7, location_name="Город")

    _, data = producer.calls[0]
    assert data["template_key"] == NoticeTemplates.SAFE_ZONE_ENTERED
    assert json.loads(data["variables"]) == {"location": "Город"}


@pytest.mark.unit
async def test_items_secured_includes_count_when_present() -> None:
    producer = FakeProducer()
    await PlayerNoticePublisher(producer).items_secured(7, count=3)

    _, data = producer.calls[0]
    assert data["template_key"] == NoticeTemplates.ITEMS_SECURED
    assert json.loads(data["variables"]) == {"count": 3}


@pytest.mark.unit
async def test_loot_claimed_carries_summary_variable() -> None:
    producer = FakeProducer()
    await PlayerNoticePublisher(producer).loot_claimed(7, summary="Ржавый клинок, Медные монеты x3")

    _, data = producer.calls[0]
    assert data["template_key"] == NoticeTemplates.LOOT_CLAIMED
    assert data["domain"] == "loot"
    assert json.loads(data["variables"]) == {"summary": "Ржавый клинок, Медные монеты x3"}


@pytest.mark.unit
async def test_combat_started_publishes_system_notice_to_many_players() -> None:
    producer = FakeProducer()
    await PlayerNoticePublisher(producer).combat_started(
        [7, 11],
        time_text="21:40",
        participants="Команда 1: Hero против Команда 2: Wolf",
    )

    event, data = producer.calls[0]
    assert event == PLAYER_NOTICE_EVENT
    assert data["template_key"] == NoticeTemplates.COMBAT_STARTED
    assert data["domain"] == "combat"
    assert data["severity"] == "warning"
    assert json.loads(data["character_ids"]) == [7, 11]
    assert json.loads(data["variables"]) == {
        "time": "21:40",
        "participants": "Команда 1: Hero против Команда 2: Wolf",
    }


@pytest.mark.unit
async def test_combat_finished_publishes_system_notice_to_many_players() -> None:
    producer = FakeProducer()
    await PlayerNoticePublisher(producer).combat_finished(
        [7, 11],
        time_text="21:44",
        outcome="победила Команда 1: Hero на ходу 12",
        participants="Команда 1: Hero; Команда 2: Wolf",
    )

    event, data = producer.calls[0]
    assert event == PLAYER_NOTICE_EVENT
    assert data["template_key"] == NoticeTemplates.COMBAT_FINISHED
    assert data["domain"] == "combat"
    assert json.loads(data["character_ids"]) == [7, 11]
    assert json.loads(data["variables"]) == {
        "time": "21:44",
        "outcome": "победила Команда 1: Hero на ходу 12",
        "participants": "Команда 1: Hero; Команда 2: Wolf",
    }


@pytest.mark.unit
async def test_corpse_items_lost_without_count_has_empty_variables() -> None:
    producer = FakeProducer()
    await PlayerNoticePublisher(producer).corpse_items_lost(7)

    _, data = producer.calls[0]
    assert data["template_key"] == NoticeTemplates.CORPSE_ITEMS_LOST
    assert json.loads(data["variables"]) == {}


@pytest.mark.unit
async def test_request_refresh_emits_refresh_presentation_without_text() -> None:
    producer = FakeProducer()
    await PlayerNoticePublisher(producer).request_refresh(
        42, target=RefreshTargets.STATUS, reason="combat_finalized", domain="combat"
    )

    assert len(producer.calls) == 1
    event, data = producer.calls[0]
    assert event == PLAYER_NOTICE_EVENT
    assert data["presentation"] == "refresh"
    assert data["target"] == "status"
    assert data["reason"] == "combat_finalized"
    assert data["domain"] == "combat"
    assert data["template_key"] == ""  # refresh carries no text
    assert json.loads(data["character_ids"]) == [42]


@pytest.mark.unit
def test_system_chat_payload_has_empty_refresh_fields() -> None:
    payload = build_player_notice_payload(
        character_ids=[1],
        template_key=NoticeTemplates.PLAYER_DEATH,
        domain="expedition",
    )
    assert payload["target"] == ""
    assert payload["reason"] == ""


class FakeRedis:
    def __init__(self) -> None:
        self.xadds: list[tuple[str, dict[str, Any]]] = []

    async def xadd(self, stream: str, fields: Any, **kwargs: Any) -> None:
        self.xadds.append((stream, fields))


@pytest.mark.unit
async def test_raw_stream_producer_writes_typed_event_to_stream() -> None:
    redis = FakeRedis()
    producer = RawStreamNoticeProducer(redis)

    await PlayerNoticePublisher(producer).player_respawned(42)

    assert len(redis.xadds) == 1
    _, encoded = redis.xadds[0]
    # encode_stream_payload returns a flat mapping; the type lives in it.
    assert "player.notice" in str(encoded)

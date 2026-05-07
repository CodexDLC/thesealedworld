from __future__ import annotations

import json

import pytest

from src.backend.features.monsters.integrations.text_ai_client import MonsterClanTextAIClient


@pytest.fixture(autouse=True)
def reset_monster_clan_text_ai_rate_limit_state():
    MonsterClanTextAIClient._rate_limit_lock = None
    MonsterClanTextAIClient._last_request_monotonic = None
    MonsterClanTextAIClient._blocked_until_monotonic = None
    MonsterClanTextAIClient._failure_backoff_seconds = 0.0
    yield
    MonsterClanTextAIClient._rate_limit_lock = None
    MonsterClanTextAIClient._last_request_monotonic = None
    MonsterClanTextAIClient._blocked_until_monotonic = None
    MonsterClanTextAIClient._failure_backoff_seconds = 0.0


class FakeAI:
    def __init__(self) -> None:
        self.calls = 0

    def include_router(self, router) -> None:
        return None

    async def process(self, prompt_name: str, **kwargs):
        self.calls += 1
        return json.dumps(
            {
                "name_ru": "Стая Холодного Камня",
                "description": "Хищники держатся у старых плит и нападают из тумана.",
                "variants_flavor": {
                    "wolf_runner": {
                        "name": "Каменный бегун",
                        "appearance": "Серая шерсть покрыта каменной пылью.",
                        "encounter": "Он выскакивает из тумана.",
                        "behavior": "Держит дистанцию и ищет слабое место.",
                    }
                },
            },
            ensure_ascii=False,
        )


class FailingAI:
    def __init__(self) -> None:
        self.calls = 0

    def include_router(self, router) -> None:
        return None

    async def process(self, prompt_name: str, **kwargs):
        self.calls += 1
        raise RuntimeError("quota")


@pytest.mark.unit
async def test_monster_clan_text_ai_client_rate_limits_between_requests(monkeypatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(
        "src.backend.features.monsters.integrations.text_ai_client.settings."
        "monster_clan_flavor_ai_interval_seconds",
        0.5,
    )
    monkeypatch.setattr("src.backend.features.monsters.integrations.text_ai_client.asyncio.sleep", fake_sleep)
    client = MonsterClanTextAIClient(FakeAI())  # type: ignore[arg-type]

    first = await client.generate_clan_flavor({})
    second = await client.generate_clan_flavor({})

    assert first is not None
    assert second is not None
    assert sleeps
    assert sleeps[0] <= 0.5


@pytest.mark.unit
async def test_monster_clan_text_ai_client_returns_none_when_ai_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.backend.features.monsters.integrations.text_ai_client.settings."
        "monster_clan_flavor_ai_interval_seconds",
        0.0,
    )
    client = MonsterClanTextAIClient(FailingAI())  # type: ignore[arg-type]

    assert await client.generate_clan_flavor({}) is None


@pytest.mark.unit
async def test_monster_clan_text_ai_client_increases_backoff_after_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.backend.features.monsters.integrations.text_ai_client.settings."
        "monster_clan_flavor_ai_interval_seconds",
        30.0,
    )
    ai = FailingAI()
    client = MonsterClanTextAIClient(ai)  # type: ignore[arg-type]

    assert await client.generate_clan_flavor({}) is None
    assert MonsterClanTextAIClient._failure_backoff_seconds == 30.0
    assert ai.calls == 1

    assert await client.generate_clan_flavor({}) is None
    assert MonsterClanTextAIClient._failure_backoff_seconds == 30.0
    assert ai.calls == 1

    MonsterClanTextAIClient._blocked_until_monotonic = None
    MonsterClanTextAIClient._last_request_monotonic = None
    assert await client.generate_clan_flavor({}) is None
    assert MonsterClanTextAIClient._failure_backoff_seconds == 40.0
    assert ai.calls == 2

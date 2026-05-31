from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.backend.infrastructure.actor_state.managers import GameSessionLockManager


class _FakeStringOps:
    """In-memory stand-in for ``RedisService.string`` used by the manager."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.last_ttl: int | None = None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self.store[key] = value
        self.last_ttl = ttl

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def expire(self, key: str, ttl: int) -> bool:
        if key not in self.store:
            return False
        self.last_ttl = ttl
        return True


def _build_manager(ttl: int = 6 * 60 * 60) -> tuple[GameSessionLockManager, _FakeStringOps]:
    string_ops = _FakeStringOps()
    redis = SimpleNamespace(string=string_ops)
    manager = GameSessionLockManager(redis, ttl_seconds=ttl)
    return manager, string_ops


@pytest.mark.unit
async def test_claim_writes_value_with_ttl() -> None:
    manager, string_ops = _build_manager(ttl=120)

    await manager.claim(42, "session-A")

    assert string_ops.store == {"game:ac_sess:42": "session-A"}
    assert string_ops.last_ttl == 120


@pytest.mark.unit
async def test_claim_overwrites_previous_session_last_login_wins() -> None:
    manager, string_ops = _build_manager()

    await manager.claim(42, "session-A")
    await manager.claim(42, "session-B")

    assert string_ops.store["game:ac_sess:42"] == "session-B"


@pytest.mark.unit
async def test_current_returns_latest_session_or_none() -> None:
    manager, _ = _build_manager()

    assert await manager.current(42) is None

    await manager.claim(42, "session-A")
    assert await manager.current(42) == "session-A"


@pytest.mark.unit
async def test_release_drops_lock_so_next_request_sees_no_session() -> None:
    manager, _ = _build_manager()
    await manager.claim(42, "session-A")

    await manager.release(42)

    assert await manager.current(42) is None


@pytest.mark.unit
async def test_touch_refreshes_ttl_only_for_existing_lock() -> None:
    manager, string_ops = _build_manager(ttl=120)
    await manager.claim(42, "session-A")
    string_ops.last_ttl = None

    await manager.touch(42)

    assert string_ops.last_ttl == 120

    # Touching a non-existent lock must not write anything.
    string_ops.last_ttl = None
    await manager.touch(999)
    assert string_ops.last_ttl is None

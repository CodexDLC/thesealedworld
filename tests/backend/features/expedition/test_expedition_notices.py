"""ExpeditionService emits player-facing notices at lifecycle points.

The lifecycle methods are DB-heavy; these tests neutralize the persistence
internals (and SQLAlchemy ``flag_modified``) and assert only the notice
emission contract — i.e. the right semantic publisher method fires at the
right moment, and the safe-sync count conditional behaves.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.backend.features.expedition import service as expedition_service_module
from src.backend.features.expedition.service import ExpeditionService


class FakePublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        async def _record(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return _record

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]


@pytest.fixture(autouse=True)
def _noop_flag_modified(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(expedition_service_module, "flag_modified", lambda *a, **k: None)


def _service(publisher: FakePublisher, **overrides) -> ExpeditionService:
    svc = ExpeditionService(
        session=AsyncMock(),
        character_sessions=None,
        expedition_repo=SimpleNamespace(
            is_processed=lambda *a, **k: False,
            mark_processed=lambda *a, **k: None,
        ),
        notice_publisher=publisher,
    )
    # Neutralize persistence-heavy helpers.
    svc._maybe_commit = AsyncMock()
    svc.refresh_session_risk = AsyncMock()
    for name, value in overrides.items():
        setattr(svc, name, value)
    return svc


@pytest.mark.asyncio
async def test_mark_death_pending_emits_player_died() -> None:
    publisher = FakePublisher()
    expedition = SimpleNamespace(status="active", run_id="r1", corpse_id="c1")
    svc = _service(publisher, get_active_run=AsyncMock(return_value=expedition))

    result = await svc.mark_death_pending(char_id=42, combat_id="combat-1", location_id="10_10")

    assert result is True
    assert "player_died" in publisher.names()


@pytest.mark.asyncio
async def test_mark_death_pending_without_active_run_emits_nothing() -> None:
    publisher = FakePublisher()
    svc = _service(publisher, get_active_run=AsyncMock(return_value=None))

    result = await svc.mark_death_pending(char_id=42, combat_id=None, location_id=None)

    assert result is False
    assert publisher.calls == []


@pytest.mark.asyncio
async def test_respawn_emits_player_respawned() -> None:
    publisher = FakePublisher()
    expedition = SimpleNamespace(status="death_pending", run_id="r1", corpse_id="c1")
    svc = _service(
        publisher,
        get_active_run=AsyncMock(return_value=expedition),
        finalize_death_corpse=AsyncMock(return_value={"status": "finalized"}),
        _restore_active_session_after_respawn=AsyncMock(),
        _respawn_result=lambda exp: {"status": "respawned"},
    )

    await svc.respawn(char_id=42)

    assert "player_respawned" in publisher.names()


@pytest.mark.asyncio
async def test_safe_sync_emits_zone_and_items_when_secured() -> None:
    publisher = FakePublisher()
    expedition = SimpleNamespace(status="active", run_id="r1")
    svc = _service(
        publisher,
        get_active_run=AsyncMock(return_value=expedition),
        _pending=lambda exp: {},
        _secure_expedition_items=AsyncMock(return_value=3),
        _secure_expedition_resources=AsyncMock(),
        _persist_pending_progress=AsyncMock(),
    )
    svc.session.get = AsyncMock(return_value=None)

    await svc.safe_sync(char_id=42, location_id="52_52", location_name="Площадь")

    assert "safe_zone_entered" in publisher.names()
    items_calls = [c for c in publisher.calls if c[0] == "items_secured"]
    assert items_calls and items_calls[0][2] == {"count": 3}


@pytest.mark.asyncio
async def test_safe_sync_skips_items_secured_when_nothing_secured() -> None:
    publisher = FakePublisher()
    expedition = SimpleNamespace(status="active", run_id="r1")
    svc = _service(
        publisher,
        get_active_run=AsyncMock(return_value=expedition),
        _pending=lambda exp: {},
        _secure_expedition_items=AsyncMock(return_value=0),
        _secure_expedition_resources=AsyncMock(),
        _persist_pending_progress=AsyncMock(),
    )
    svc.session.get = AsyncMock(return_value=None)

    await svc.safe_sync(char_id=42, location_id="52_52", location_name="Площадь")

    names = publisher.names()
    assert "safe_zone_entered" in names
    assert "items_secured" not in names


@pytest.mark.asyncio
async def test_safe_sync_without_active_run_emits_nothing() -> None:
    publisher = FakePublisher()
    svc = _service(publisher, get_active_run=AsyncMock(return_value=None))

    await svc.safe_sync(char_id=42, location_id="52_52", location_name="Площадь")

    assert publisher.calls == []

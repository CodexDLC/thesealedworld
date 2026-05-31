from __future__ import annotations

from typing import Any

import pytest


class _FakeLogger:
    def __init__(self, events: list[tuple[str, str, dict[str, Any]]], fields: dict[str, Any] | None = None) -> None:
        self._events = events
        self._fields = fields or {}

    def bind(self, **fields: Any) -> _FakeLogger:
        return _FakeLogger(self._events, {**self._fields, **fields})

    def info(self, message: str) -> None:
        self._events.append(("info", message, dict(self._fields)))

    def warning(self, message: str) -> None:
        self._events.append(("warning", message, dict(self._fields)))

    def exception(self, message: str) -> None:
        self._events.append(("exception", message, dict(self._fields)))


@pytest.mark.asyncio
async def test_logged_task_logs_visible_start_and_finish(monkeypatch) -> None:
    import src.shared.infrastructure.log_task_wrapper as task_wrapper

    events: list[tuple[str, str, dict[str, Any]]] = []
    contexts: list[dict[str, Any]] = []
    cleared = False

    def fake_set_log_context(**context: Any) -> None:
        contexts.append(context)

    def fake_clear_log_context() -> None:
        nonlocal cleared
        cleared = True

    monkeypatch.setattr(task_wrapper, "logger", _FakeLogger(events))
    monkeypatch.setattr(task_wrapper, "set_log_context", fake_set_log_context)
    monkeypatch.setattr(task_wrapper, "clear_log_context", fake_clear_log_context)

    @task_wrapper.logged_task
    async def combat_ai_live_simulation_task(ctx: dict[str, Any], payload: dict[str, Any]) -> str:
        return "ok"

    result = await combat_ai_live_simulation_task({}, {"run_id": "run-1"})

    assert result == "ok"
    assert contexts[0]["task_name"] == "combat_ai_live_simulation_task"
    assert contexts[0]["run_id"] == "run-1"
    assert cleared is True
    assert [event[1] for event in events] == [
        "CombatAiLiveSimulationTaskStarted",
        "CombatAiLiveSimulationTaskFinished",
    ]
    assert events[0][2]["run_id"] == "run-1"
    assert events[1][2]["status"] == "completed"
    assert "duration_ms" in events[1][2]


@pytest.mark.asyncio
async def test_logged_task_logs_failure(monkeypatch) -> None:
    import src.shared.infrastructure.log_task_wrapper as task_wrapper

    events: list[tuple[str, str, dict[str, Any]]] = []

    monkeypatch.setattr(task_wrapper, "logger", _FakeLogger(events))
    monkeypatch.setattr(task_wrapper, "set_log_context", lambda **context: None)
    monkeypatch.setattr(task_wrapper, "clear_log_context", lambda: None)

    @task_wrapper.logged_task
    async def combat_ai_live_simulation_task(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await combat_ai_live_simulation_task({}, {"run_id": "run-1"})

    assert [event[1] for event in events] == [
        "CombatAiLiveSimulationTaskStarted",
        "CombatAiLiveSimulationTaskFailed",
    ]
    assert events[1][0] == "exception"
    assert events[1][2]["status"] == "failed"

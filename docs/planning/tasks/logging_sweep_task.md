# Logging Codebase Sweep Task

## Goal

Refactor all ~240 logger calls across ~99 files to follow `docs/logging-rules.md`.
Infrastructure (middleware, metrics, setup) is already in place — this task only
touches existing log statements.

## Prerequisites

Read `docs/logging-rules.md` before starting. The rules document is the authority
on log levels, structured patterns, naming conventions, and what not to log.

New infrastructure files already exist:
- `src/shared/log_middleware.py` — `LogContextMiddleware` (request_id, char_id, healthcheck)
- `src/shared/log_task_wrapper.py` — `@logged_task` decorator
- `src/shared/metrics.py` — Prometheus registry
- `codex_core.common.log_context` — `set_log_context`, `clear_log_context`

## Rules (apply to every file)

### 1. No f-strings in logger calls

```python
# BEFORE
logger.info(f"Combat lifecycle ready: combat_id={cid}")
# AFTER
logger.bind(combat_id=cid).info("CombatLifecycleReady")
```

### 2. Move key=value from message string to logger.bind()

```python
# BEFORE
logger.info("Event published: type={} message_id={} correlation_id={}", event_type, mid, cid)
# AFTER
logger.bind(event_type=event_type, message_id=mid, correlation_id=cid).info("EventPublished")
```

### 3. PascalCase event names in messages

```python
# BEFORE
logger.info("Backend startup started")
# AFTER
logger.info("BackendStartupStarted")
```

### 4. Pipe-separator pattern to bind

```python
# BEFORE
logger.info("WorkerInit | stage=start worker_type=combat")
# AFTER
logger.bind(stage="start", worker_type="combat").info("WorkerInit")
```

### 5. Re-level noisy logs

Move to DEBUG:
- Per-request backend API calls in `src/frontend/core/api.py`
- Token refreshes (routine, not failures)
- Page view loads (lobby, menu, etc.)
- `CombatCreationTiming` intermediate steps (keep `step=total` at INFO)
- Cache lookups, condition evaluations, variable dumps

Keep at INFO:
- Startup/shutdown lifecycle events
- Auth login/logout events
- Business boundary events (combat created, scenario advanced, session started)
- Worker init/shutdown

### 6. Remove emoji from log messages

Affects `src/frontend/core/static.py` and any other file.

### 7. Add @logged_task decorator to all ARQ tasks

In files: `src/backend/features/combat/workers/`, `src/backend/features/system/workers/`,
`src/backend/features/generation_ai/workers/`, `src/backend/features/loot/workers/`.

```python
from src.shared.log_task_wrapper import logged_task

@logged_task
async def my_task(ctx, payload):
    ...
```

### 8. Add correlation_id propagation in event handlers

In each `@router.on()` handler (10 files under `src/backend/features/*/events/`):

```python
from codex_core.common.log_context import set_log_context, clear_log_context

@router.on("some.event")
async def handle(event):
    set_log_context(correlation_id=event.correlation_id)
    try:
        ...
    finally:
        clear_log_context()
```

### 9. Never use logger.error(f"Failed: {e}")

```python
# BEFORE
logger.error(f"Failed: {e}")
# AFTER (inside except block)
logger.exception("OperationFailed")
```

## Processing Order

1. `src/backend/core/` — bus/producer (done), middleware, arq, lifespan, containers
2. `src/backend/features/*/events/` — 10 event handler files
3. `src/backend/features/*/workers/` — 4 worker types
4. `src/backend/features/*/services/` — business logic
5. `src/backend/features/*/api/` — HTTP handlers
6. `src/frontend/core/` — api client, middleware, static
7. `src/frontend/features/` + `src/frontend/game_features/`
8. `src/backend/chat/`

## Verification

After completing the sweep:

```bash
# No f-strings in logger calls
grep -rn 'logger\.\(info\|debug\|warning\|error\|exception\|critical\)(f"' src/

# No pipe-separator pattern
grep -rn 'logger\.info(".*|.*=.*"' src/

# Tests pass
python -m pytest

# Type check
python -m mypy src/
```

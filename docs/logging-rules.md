# Logging Rules

This document is the single source of truth for how every log call in TurnBasedMMORPG must be written.
Referenced by the `turnbasedmmorpg-logging-quality` agent skill and the codebase sweep task.

## Log Levels

| Level | When | Prod stdout | Examples |
|-------|------|-------------|----------|
| DEBUG | Internal logic decisions, flow tracing, cache hit/miss, condition evaluation | no | `ScenarioConditionEvaluated`, `CacheHit` |
| INFO | Business event at an operation boundary (one per logical operation) | yes | `CombatSessionCreated`, `WorkerInit`, `AuthLoginAccepted` |
| WARNING | Unexpected but recoverable condition; the request/job continues | yes | `AuthRefreshRejected`, `DirtySyncSkipped`, `LootOrderIgnored` |
| ERROR | Operation failed; the request/job cannot complete its primary purpose | yes | `DatabaseWriteFailed`, `ExternalApiError` |
| CRITICAL | Process-level failure; the service cannot function | yes | `StartupFailed`, `ShutdownFailed` |

Rules of thumb:

- If the log fires on every request or every iteration, it is probably DEBUG, not INFO.
- If the log fires once at startup/shutdown, it is INFO.
- If you are catching an exception and re-raising or returning an error response, use ERROR.
- If you are catching an exception and falling back to a default, use WARNING.
- Reserve CRITICAL for lifespan failures only.

## Structured Logging Pattern

All context fields MUST use `logger.bind()`, not string interpolation in the message.
The message string must be a short, human-readable **PascalCase event name**.

```python
# CORRECT: context in bind, message is a short PascalCase event name
logger.bind(combat_id=cid, actor_count=len(actors)).info("CombatLifecycleReady")

# CORRECT: simple single-field case with Loguru placeholder
logger.info("RegistryLoaded variant_count={}", count)

# WRONG: f-string — breaks deferred formatting and structured extraction
logger.info(f"Combat lifecycle ready: combat_id={cid}")

# WRONG: all fields in message string — Loki cannot extract them
logger.info("Combat lifecycle ready: combat_id={} source={}", id, src)

# WRONG: pipe-separator convention (legacy) — move fields to bind
logger.info("WorkerInit | stage=start worker_type=combat")

# CORRECT replacement for the above
logger.bind(stage="start", worker_type="combat").info("WorkerInit")
```

### When to use `logger.bind()` vs Loguru `{}`

- **`logger.bind()`** (preferred): Use for all context fields that should be machine-extractable.
  Fields in `bind()` appear in the JSON `extra` dict and become Loki labels/structured metadata.
- **Loguru `{}`**: Acceptable only for a single, simple, self-explanatory value that adds clarity
  to the human-readable message. Example: `logger.info("RegistryLoaded variant_count={}", 52)`.
- **Never use f-strings or `%` formatting** with logger calls.

## Context Fields

### Automatic (injected by infrastructure, never bind manually)

| Field | Source | Always present |
|-------|--------|----------------|
| `service` | `setup_logging` patcher | yes |
| `request_id` | `LogContextMiddleware` / `@logged_task` | yes |

### Semi-automatic (injected by middleware/decorator when available)

| Field | Source | When |
|-------|--------|------|
| `char_id` | middleware path params / task payload | when path contains char_id |
| `task_name` | `@logged_task` decorator | worker tasks only |
| `correlation_id` | event handler wrapper | event bus handlers |

### Manual (bind explicitly in business code)

| Field | When |
|-------|------|
| `session_id` | game session context (combat, scenario, exploration) |
| `combat_id` | combat domain operations |
| `quest_key` | scenario domain operations |
| `user_id` | auth/account flows only (use char_id for game flows) |
| `duration_ms` | timed operations (always float, always milliseconds) |

## Dev vs Prod Behavior

| Aspect | Dev (`DEBUG=True`) | Prod (`DEBUG=False`) |
|--------|-------------------|---------------------|
| Console format | Colorized human-readable | JSON (`serialize=True`) |
| File sinks | `debug.log` + `errors.json` | None (Docker stdout only) |
| Console level | DEBUG | INFO |
| Healthcheck logs | Visible | Filtered (suppressed) |
| Backtrace / diagnose | Enabled | Disabled |

In production, Docker captures stdout. Alloy collects it and ships to Grafana Cloud Loki.
File sinks are unnecessary and would consume disk on the container.

## What NOT to Log

- **Healthcheck requests** (`/health`) — filtered automatically by middleware.
- **Request/response bodies** — PII risk; log metadata only (method, path, status, duration).
- **Tokens, passwords, API keys** — never, under any circumstances.
- **Per-item loop iterations** — log a summary after the loop, not each item.
- **Static file serving** — creates noise with no diagnostic value.
- **Routine token refreshes** — use DEBUG, not INFO.
- **Page view loads** — use DEBUG unless it is a business-significant event.

## Naming Conventions

### Field names

Always `snake_case`:

- IDs: suffix `_id` — `char_id`, `combat_id`, `session_id`, `user_id`
- Durations: always `duration_ms` (float, milliseconds)
- Counts: suffix `_count` — `actor_count`, `variant_count`, `commitment_count`
- Keys: suffix `_key` when it is a string key, not a numeric ID — `quest_key`

### Event names (message string)

Always **PascalCase**, domain-prefixed where useful:

- `CombatSessionCreated`, `CombatLifecycleReady`, `CombatMoveSubmitted`
- `ScenarioNodeAdvanced`, `ScenarioStepCompleted`
- `WorkerInit`, `WorkerShutdown`, `TaskStarted`, `TaskCompleted`
- `AuthLoginAccepted`, `AuthRefreshRejected`
- `EventPublished`, `EventRequestStarted`, `EventRequestCompleted`
- `LootOrderProcessed`, `InventoryItemAdded`

Do not use:
- Sentences: `"Combat session was created successfully"`
- Snake_case: `"combat_session_created"`
- Emoji in messages

## Examples by Service Type

### HTTP handler (backend/frontend)

```python
# request_id and char_id injected automatically by LogContextMiddleware
logger.bind(move_type=move.type).info("CombatMoveSubmitted")
```

### Worker task (ARQ)

```python
@logged_task
async def combat_collector_task(ctx, payload):
    # request_id, task_name, char_id, combat_id injected by decorator
    logger.info("TaskStarted")
    # ... work ...
    logger.bind(duration_ms=elapsed).info("TaskCompleted")
```

### Event handler (Redis Streams)

```python
@router.on("combat.result")
async def handle_combat_result(event):
    # correlation_id injected by event handler wrapper
    logger.bind(session_id=sid, outcome=outcome).info("CombatResultProcessed")
```

### Middleware

```python
# Only log warnings/errors in middleware, not normal flow
logger.bind(char_id=char_id).warning("DirtySyncCheckFailed")
```

### Startup / shutdown (lifespan)

```python
logger.info("BackendStartupStarted")
# ... bootstrap ...
logger.bind(duration_ms=elapsed).info("BackendStartupComplete")
```

## Exceptions and Tracebacks

- Use `logger.exception("EventName")` inside `except` blocks — it auto-attaches the traceback.
- Use `logger.opt(exception=True).critical("EventName")` for CRITICAL with traceback outside except.
- Never use `logger.error(f"Failed: {e}")` — use `logger.exception("OperationFailed")` instead.
- The `errors.json` sink (dev) and JSON stdout (prod) automatically serialize exception info.

## Prometheus Metrics (separate from logs)

Application-level metrics are exposed via `/metrics` endpoint on HTTP services.
See `src/shared/metrics.py` for the registry. Metrics and logs are complementary:

- **Metrics** answer "how much / how fast" — request rate, latency percentiles, error rate.
- **Logs** answer "what happened" — specific event details, error context, correlation traces.

Do not duplicate metric data in log messages. If you are logging a duration, bind it as
`duration_ms` for Loki queries, but the canonical latency data comes from Prometheus histograms.

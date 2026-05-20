---
name: turnbasedmmorpg-logging-quality
description: Use when reviewing or writing code that includes logger calls, when adding new features that should have logging, or before commits that touch files importing loguru. Enforces structured logging standards from docs/logging-rules.md.
---

# Logging Quality Gate

## When to Apply

- Any file being created or modified that imports `from loguru import logger`.
- Any new HTTP endpoint, ARQ task, or event handler.
- Before declaring code complete (runs before `turnbasedmmorpg-quality-gate`).

## Rules Reference

Full rules in `docs/logging-rules.md`. Summary of checks:

## Checks

### 1. No f-strings in logger calls

```python
# WRONG
logger.info(f"thing={x}")
# RIGHT
logger.bind(thing=x).info("ThingProcessed")
```

### 2. Context fields in bind, not in message

All key=value data must use `logger.bind()`, not string formatting.

### 3. PascalCase event names

Message string must be a short PascalCase name: `"CombatSessionCreated"`,
not `"Combat session created"` or `"combat_session_created"`.

### 4. Correct log level

- DEBUG: internal logic, flow tracing, cache hits
- INFO: business events at operation boundaries (one per operation)
- WARNING: recoverable anomalies
- ERROR: operation failures
- CRITICAL: process-level failures only

If a log fires on every request or every iteration, it should be DEBUG.

### 5. No PII in logs

Never log tokens, passwords, request/response bodies, or API keys.

### 6. @logged_task on ARQ tasks

Every async task function registered in `*_TASKS` lists must be decorated
with `@logged_task` from `src.shared.log_task_wrapper`.

### 7. correlation_id in event handlers

Every `@router.on()` handler must propagate `correlation_id` via
`set_log_context(correlation_id=event.correlation_id)` and clear in finally.

### 8. No emoji in log messages

### 9. Exceptions use logger.exception()

Inside `except` blocks use `logger.exception("EventName")`, never
`logger.error(f"Failed: {e}")`.

## Report Format

When checking logging quality, report:

```
Logging Quality: [PASS / N issues found]
- [file:line] issue description
```

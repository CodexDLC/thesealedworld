---
name: turnbasedmmorpg-log-diagnosis
description: Use when the user pastes logs, tracebacks, console output, docker logs, request logs, healthcheck output, or asks what a log means in TurnBasedMMORPG. Treat pasted logs as diagnosis-only unless the user explicitly asks to edit or fix files.
---

# TurnBasedMMORPG Log Diagnosis

## Default Mode

Pasted logs mean: analyze, explain, and propose a fix plan.

They do not authorize code edits, file creation, migrations, container restarts, destructive cleanup, or "obvious" fixes.

## Required Response

When the user sends logs or asks what happened:

1. Identify the failing service, request, exception, and timestamp if present.
2. Separate evidence from inference.
3. State whether the log proves a current bug, a startup/reload race, stale browser/session state, missing dependency, bad data, or an unavailable service.
4. If useful, inspect code/config/read-only container state to confirm the diagnosis.
5. Return a concise report:
   - `Причина`
   - `Доказательства из лога`
   - `Что проверить`
   - `План исправления`
6. Stop and wait for an explicit "чини", "исправь", "внеси правку", "сделай фикс", or equivalent before editing files.

## Allowed Without Explicit Fix Request

- Read files.
- Search code.
- Read container status/logs.
- Run non-mutating diagnostics.
- Run tests only if they are used to confirm the diagnosis and do not require code changes.

## Not Allowed Without Explicit Fix Request

- Applying patches.
- Creating files.
- Editing configuration.
- Restarting containers.
- Running migrations.
- Deleting Redis/DB/session state.
- Adding fallback behavior to make a log disappear.

## If The Fix Looks Obvious

Still do not edit. Say:

```text
Нашел причину и могу исправить. Сейчас без правок: <short plan>. Чинить?
```

## Interaction With Other Skills

This skill reinforces `ask-before-editing`. If another project skill suggests implementation work, this log-diagnosis rule wins until the user explicitly asks for a fix.

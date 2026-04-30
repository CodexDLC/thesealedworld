---
name: turnbasedmmorpg-quality-gate
description: Final code verification guidance for TurnBasedMMORPG. Use before declaring implementation complete, after code edits, before commits or PRs, and whenever deciding which local validation command to run, especially tools/dev/check.py, lint/type/security/test gates, --ci mode, or targeted fallback checks.
---

# TurnBasedMMORPG Quality Gate

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-quality-gate/references/check-commands.md`
- `tools/dev/README.md`
- `tools/dev/check.py`

## Core Rule

Before saying code work is complete, run the strongest practical local verification for the changed surface.

Prefer the project gate:

```powershell
uv run python tools/dev/check.py
```

For CI-like fail-fast behavior:

```powershell
uv run python tools/dev/check.py --ci
```

If `uv run python` is not available in the current environment, use the active project Python only when it works. Do not silently skip verification; report the exact failure.

## Current Gate

At the time this skill was written, `tools/dev/check.py` runs:

- pre-commit hooks on all files
- mypy over `src` and `tools`
- pip-audit with the project ignore list
- pytest

The current script recognizes `--ci` behavior. Do not assume `--lint`, `--all`, or other flags exist unless `tools/dev/check.py` or `tools/dev/README.md` shows them.

## Reporting

In the final response, state which command was run and whether it passed.

If the gate could not run, state why and list the strongest fallback checks that did run.

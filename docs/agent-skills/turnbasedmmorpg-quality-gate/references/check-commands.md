# Check Commands

## Preferred Full Gate

Use after broad code changes, before commits, before PRs, and before declaring a task complete:

```powershell
uv run python tools/dev/check.py
```

Use CI mode when a failing step should stop immediately with a non-zero exit:

```powershell
uv run python tools/dev/check.py --ci
```

## What The Gate Runs

Current `tools/dev/check.py` runs these steps from the repository root:

```powershell
uv run pre-commit run --all-files
uv run mypy --explicit-package-bases src tools
uv run pip-audit --skip-editable --ignore-vuln CVE-2026-3219
uv run pytest
```

## Targeted Fallbacks

Use targeted fallbacks only when the full gate is too expensive, blocked, or not proportional to the change.

For backend tests:

```powershell
uv run pytest tests/backend
```

For shared contract tests:

```powershell
uv run pytest tests/shared
```

For a specific test file:

```powershell
uv run pytest path/to/test_file.py
```

For type checking:

```powershell
uv run mypy --explicit-package-bases src tools
```

For hooks/lint formatting:

```powershell
uv run pre-commit run --all-files
```

## Flag Discipline

Before using flags like `--lint`, `--all`, or `--fix`, confirm they exist in `tools/dev/check.py` or `tools/dev/README.md`.

If a user asks for a flag that does not exist, either update the checker intentionally as a separate code change or explain that the current checker does not support it.

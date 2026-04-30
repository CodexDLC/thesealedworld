# Testing Strategy

This project follows the testing methodology recorded in MCP memory:
`MASTER_INDEX -> SEC:Methodology`, including the nodes `Подход к тестированию Python-библиотек`
and `Конфигурация coverage для Python-проекта`.

## Test Pyramid

TurnBasedMMORPG is a production application, not a standalone library. The target pyramid is:

1. Unit tests: isolated domain and service logic.
2. Integration tests: database, Redis, API, event bus, and feature boundaries.
3. E2E tests: browser/game flows after the migration and refactor stabilize.

During active migration, new code should start with clean unit tests. Integration and E2E coverage should be added once the moved feature boundaries are stable.

## Coverage Targets

Target project coverage is 90% or higher.

Core modules are treated as critical infrastructure and should reach 100% coverage where practical. Provider and dependency wiring code should target 90% or higher.

Coverage configuration should live in `pyproject.toml` under `[tool.coverage.report]` using `fail_under = 90`. Do not put `--cov-fail-under` in pytest `addopts`, because that makes selective test runs unnecessarily painful.

Recommended pytest addopts shape:

```toml
addopts = "--tb=short --cov=src --cov-report=term-missing"
```

## Test Layout

Tests live outside `src/` under the repository-level `tests/` package.

The target structure separates application layers first, then feature domains:

```text
tests/
  conftest.py
  backend/
    conftest.py
    core/
      redis/
      bus/
      database/
    features/
      auth/
      game_lobby/
      actor_state/
      scenario/
      combat/
      inventory/
      exploration/
      world/
  frontend/
    conftest.py
    core/
    features/
      auth/
      game_lobby/
      cabinet/
    integrations/
      backend_api/
  shared/
    conftest.py
    schemas/
    enums/
```

When a domain grows, split by test level inside the domain:

```text
tests/backend/features/game_lobby/
  unit/
  integration/
```

For small domains, keeping test files directly under the domain folder is acceptable until the split improves clarity.

## Naming

Use explicit names that describe behavior:

```text
test_character_session_manager.py
test_game_lobby_creation.py
test_backend_game_lobby_api.py
```

Prefer one behavior per test. Avoid broad scenario tests that assert many unrelated details.

## Fixtures

Use layered fixtures:

- `tests/conftest.py`: global pytest setup shared by every layer.
- `tests/backend/conftest.py`: backend app, DB, Redis, event bus, auth helpers.
- `tests/frontend/conftest.py`: frontend app/client/template helpers.
- `tests/shared/conftest.py`: shared schema and enum helpers.
- domain-local `conftest.py`: only when the domain needs reusable setup.

Patch objects where they are used, not where they are declared. Prefer `unittest.mock.AsyncMock` and `MagicMock` for isolated unit tests.

## Current Development Rule

While migration is ongoing:

- write unit tests first;
- keep tests deterministic and isolated;
- avoid E2E until the UI and backend contracts settle;
- add integration tests for Redis/DB/API only when the behavior crosses a real boundary;
- do not depend on `temp/` in tests except as donor reference comments or fixtures during transitional work.

## Exclusions

Use `pragma: no cover` only for branches that cannot be exercised without breaking isolation, such as:

- defensive `except ImportError` blocks;
- explicit `raise ImportError` compatibility branches;
- environment-specific fallback paths that are covered by deployment smoke checks instead.

Do not exclude ordinary error handling just because it is inconvenient to test.

## Quality Gate

Use the project quality runner for full checks:

```powershell
uv run python tools/dev/check.py
```

Focused development runs may use direct pytest commands, for example:

```powershell
uv run pytest tests/backend/features/game_lobby -m unit
```

Before merging larger feature work, run the full quality gate and include integration tests for every touched external boundary.

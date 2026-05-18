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

Target project coverage is 90% or higher, with an interim pre-alpha threshold set appropriately in `pyproject.toml` (e.g., `fail_under = 74`).

### AI-Agent Development Constraints (The "AI Squad" Workflow)

When developing with AI agents, strict rules apply to prevent technical debt:

1. **Patch Coverage Strictness:** Any *new* code written by an agent must have 100% patch coverage. The agent must write tests for its own logic before declaring the task complete. Do not break existing tests, and do not lower the global coverage.
2. **The Boy Scout Rule (Coverage Expansion):** If an agent modifies an existing feature or module (e.g., an item service) that lacks tests, the agent MUST write tests to cover the surrounding uncovered logic in the module they just touched. This organic expansion is how legacy debt is paid down.
3. **Tech Debt Quotas (Refactoring Sessions):** For heavy legacy modules (e.g., `expedition/service.py`, `engine/resolver.py`), do not write "dummy" tests just for lines. Instead, allocate dedicated AI sessions purely to refactor and test specific edge cases or behaviors within those files.
4. **Critical Boundaries:** Modules touching `auth/session`, `migrations`, `config parsing`, and critical state transitions must aim for strict 90%+ local coverage.

Coverage configuration lives in `pyproject.toml` under `[tool.coverage.report]`. Do not put `--cov-fail-under` in pytest `addopts`.

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

### Test Doubles over Heavy Mocks

For AI-assisted development, **In-Memory Doubles (Fakes)** are vastly superior to heavy `MagicMock`/`patch` configurations.

- Avoid relying on complex `unittest.mock` assertions for infrastructure like Redis or the Database.
- Instead, create or reuse simple `InMemoryRepository` or `FakeRedisService` classes that store data in Python `dict`s and implement the same Protocol.
- This ensures tests execute quickly, verify actual logical transitions, and prevent agents from writing brittle, configuration-bound tests. Patch objects where they are used only if a Fake is unavailable.

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

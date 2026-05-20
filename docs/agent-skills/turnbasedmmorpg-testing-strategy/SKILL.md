---
name: turnbasedmmorpg-testing-strategy
description: Testing guidelines and coverage targets for TurnBasedMMORPG, especially for AI-assisted development. Use this before writing tests, deciding on coverage limits, or choosing between Mocks and In-Memory Doubles.
---

# TurnBasedMMORPG Testing Strategy for AI Agents

## Core Directives

When writing tests or evaluating coverage for this project, you MUST strictly adhere to the guidelines outlined in:

- `docs/ru/management/testing_strategy.md`

## Key AI-Workflow Rules

1. **Patch Coverage Strictness:** Any *new* code you write must have 100% patch coverage. Write tests for your logic before declaring completion. Do not lower the global coverage.
2. **The Boy Scout Rule (Coverage Expansion):** If you modify an existing feature or module that is poorly tested, you MUST write tests to cover the surrounding uncovered logic in that module. This organic "clean up as you go" method is how coverage debt is paid down.
3. **Tech Debt Quotas:** When refactoring heavy legacy files, do not write dummy/meaningless getter tests to inflate coverage. Refactoring sessions should target specific edge cases and actual behavior.
4. **In-Memory Doubles:** Prefer creating `InMemoryRepository` or `FakeRedisService` (using Python `dict`s) over complex `MagicMock` or `patch` setups when interacting with database/Redis layers. This guarantees faster, less brittle testing.
5. **Target Thresholds:** The global coverage threshold is managed in `pyproject.toml` (e.g., `fail_under = 74` during pre-alpha). Do not attempt to force 90% globally across legacy code in a single PR, but aim for 90%+ in critical boundaries (Auth, Config, State Transitions).

Read `docs/ru/management/testing_strategy.md` for complete details before implementing extensive test suites.

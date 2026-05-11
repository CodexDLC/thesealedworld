---
name: turnbasedmmorpg-anti-workaround-gate
description: Refactor integrity and anti-workaround rules for TurnBasedMMORPG. Use before adding compatibility fallbacks, legacy bridges, duplicate DTOs or schemas, adapter shims, soft migrations, temporary branches, broad fallback behavior, or any workaround instead of a clean refactor.
---

# TurnBasedMMORPG Anti Workaround Gate

## Core Rule

Do not silently add workarounds.

When the correct implementation requires refactoring, contract cleanup, deleting old paths, migrating callers, changing ownership boundaries, or removing a legacy layer, stop before adding a shortcut and ask the user which path to take.

The agent does not decide alone that technical debt is acceptable.

## What Counts As A Workaround

A workaround includes:

- compatibility fallback
- legacy bridge
- duplicate DTO, model, schema, or enum
- adapter shim that exists only to avoid changing callers
- broad `try/except` fallback that hides invalid state
- "temporary" branch with no removal plan
- parallel old/new code path
- silent default for missing invalid catalog, config, or runtime data
- string parsing where a structured project contract should be used
- copying business logic into another layer instead of moving ownership
- bypassing a feature `integrations/` boundary
- changing shared contracts to satisfy one local caller

## Required Behavior

Before adding a workaround, report:

1. What the clean solution is.
2. Why it is larger, slower, or riskier.
3. What workaround is tempting.
4. What technical debt the workaround creates.
5. Which files, contracts, or ownership boundaries are affected.
6. Ask the user to choose.

Use this shape:

```text
I see two paths:

Clean path:
- <what changes>
- <risk/cost>

Workaround path:
- <what shortcut>
- <debt/risk>

I recommend <clean/workaround> because <reason>.
Do you want me to proceed with the clean refactor or allow the workaround?
```

## Refactoring Rule

During refactoring, prefer completing the refactor over preserving dead compatibility.

Do not keep old code "just in case" unless the user explicitly asks for compatibility or there is a real external consumer that cannot be migrated in the same task.

## When To Proceed Without Asking

Proceed normally when:

- the change follows existing project patterns
- no duplicate contract is introduced
- no legacy path is preserved
- no ownership boundary is bypassed
- no fallback hides invalid data
- the solution is clearly local and reversible

Do not ask for every small implementation detail. Ask only when the choice is clean refactor versus workaround or when the workaround creates lasting technical debt.

## Hard Stop Cases

Always ask before:

- adding a second source of truth
- keeping both old and new systems active
- introducing a migration shim
- bypassing a feature integration layer
- changing shared DTOs only to satisfy one local caller
- adding fallback behavior that hides invalid catalog, config, or runtime data
- duplicating business logic across backend, frontend, runtime, or shared layers
- preserving deprecated behavior during a refactor without a removal condition

## Project Context

Use with:

- `turnbasedmmorpg-project` for ownership and source-tree rules
- `turnbasedmmorpg-backend` before backend feature or integration work
- `turnbasedmmorpg-feature-slice` for end-to-end feature changes
- `turnbasedmmorpg-skill-catalog` for in-game skill catalog work
- `turnbasedmmorpg-item-resources` for item resource refactors
- `turnbasedmmorpg-combat-contract` for combat runtime and actor snapshot contracts

## Final Reporting

If the user approves a workaround, mark it clearly in the final response:

```text
Workaround approved by user:
- <what was added>
- <why>
- <removal condition or follow-up>
```

If the user chooses the clean path, do not leave the workaround behind.

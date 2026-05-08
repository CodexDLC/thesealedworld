---
name: turnbasedmmorpg-parallel-design-prompts
description: Use with parallel-prompt-architect when creating multiple autonomous prompts for TurnBasedMMORPG architecture, data catalog, combat logs, frontend, backend, or game data design. Defines project-specific shared layers that leaf prompts must not touch.
---

# TurnBasedMMORPG Parallel Design Prompts

## Core Rule

When creating multiple prompts for this project, keep leaf prompts isolated by data/resource layer. Do not put shared integration work into every leaf prompt.

Use this skill together with `parallel-prompt-architect`.

## Shared Layers

Leaf prompts must not ask workers to edit, wire, or integrate these shared layers:

- `src/backend/features/combat/runtime/services/log_builder.py`
- combat resolver, pipeline, mechanics service, ability service, or executor runtime
- frontend combat log templates, view models, CSS, JavaScript, or generated assets
- API response contracts used by current screens
- shared DTOs consumed by multiple runtime/frontend layers
- compiler outputs
- migrations
- tests that require cross-layer integration

Only the final integrator prompt may discuss changes to these layers as implementation work.

## Safe Leaf Layers

Leaf prompts may design isolated data/resource layers:

- basic exchange and mastery catalog shape
- trigger descriptive catalog shape
- effect descriptive catalog shape
- ability, gift, and item action descriptive catalog shape
- monster taxonomy and family overlay shape
- token and term tooltip catalog shape

Unless the user explicitly asks for implementation, each leaf prompt must request a design document and local examples only.

## Required Leaf Wording

Every design-only leaf prompt must include:

```text
This is a design/data contract task only.
Do not edit code.
Do not modify log_builder, resolver, combat runtime, frontend, API, compiler outputs, generated files, tests, migrations, or shared integration code.
Only return a design document, schema proposal, and examples for this isolated layer.
If integration with log_builder or frontend is needed, describe it only as a future integration note.
```

## Final Integrator Prompt

The final prompt owns the merge:

- compare all leaf designs
- choose one shared DTO/data contract
- resolve naming conflicts
- define migration order
- list exact future integration points
- propose implementation steps only after the data layers are reconciled

The final prompt must consume outputs from the leaf prompts and must not ask leaf workers to solve the shared integration again.

## Boundary Check

Before delivering project prompts, verify:

- no leaf prompt mentions `log_builder` as a file to edit
- no leaf prompt tells a worker to wire frontend or runtime
- no two leaf prompts own the same DTO or shared consumer
- all shared work is reserved for the final integrator prompt

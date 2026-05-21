# Rift Task Pack

This folder tracks rifts as a core game mechanic. It separates design intent from implementation task groups.

## Files

- `design.md` - current mechanic design and confirmed decisions.
- `tasks_mvp.md` - first playable quest-rift slice.
- `tasks_backend.md` - backend feature, data, API, runtime, and integration tasks.
- `tasks_frontend.md` - browser UI and game-session tasks.
- `tasks_generation_balance.md` - rift generation, encounter budget, monster placement, and simulations.
- `tasks_content_lore.md` - rift settings, LLM content, monster families, references, and site roadmap.
- `open_questions.md` - decisions that need project-owner input before or during implementation.

## Ownership

The project owner is the final decision maker for unclear design points. In task files, unresolved design points are marked as:

```text
Needs owner decision
```

Use those markers to pause the implementation task and ask for clarification instead of inventing permanent rules.

## Current Scope

MVP focuses on personal quest rifts:

- Adventurers guild contract board.
- One selected contract creates/selects a personal rift entrance.
- Travel to the rift is gameplay.
- Rift exploration uses graph nodes.
- Encounters are built from gear-score budget.
- Monster rewards provide symbiote progress and rift materials.
- The run ends around rift-core handling.

Anchor rifts, public outbreaks, clan outposts, portal circles, and territory suppression are documented future layers, not MVP.

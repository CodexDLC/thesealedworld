# Project Rules

## Source Tree

Use `src/` as the target application tree:

```text
src/
  backend/
  frontend/
  shared/
```

Use `temp/` only as donor code. It may contain useful algorithms, resource data, old services, and old DTO ideas, but its layout is not the target architecture.

## Ownership

Backend features own game behavior, persistence, runtime state, events, and workers.

Frontend features own browser routes, page/fragment orchestration, forms, view models, and templates.

Shared code owns only stable contracts used by both backend and frontend.

## Boundaries

Do not import `src.backend.features` from frontend code.

Do not put frontend view models in shared code.

Do not put backend-internal service DTOs in shared code.

Do not create global repositories or global Redis managers that know every game domain.

Do not recreate a central dispatcher that replaces feature ownership.

## Donor Code Migration

When migrating from `temp/`:

1. Identify the behavior or data being kept.
2. Place it inside the owning `src/backend/features/<feature>` or `src/frontend/features/<feature>`.
3. Rename files and classes to match the current feature vocabulary.
4. Replace direct cross-feature calls with API contracts or Redis Streams events.
5. Add or update focused tests for the migrated behavior.

## Shared Contracts

Use `src/shared` only for models/enums used by both sides at an explicit boundary.

Good candidates:

- backend API request models used by frontend clients
- backend API response models parsed by frontend clients
- stable enums used by those API contracts

Bad candidates:

- frontend template view models
- backend repository models
- Redis runtime internals not exposed by API, including `game:ac:<char_id>` active character sessions and `game:actor:snapshot:*` temporary actor projections
- temporary helper schemas used only on one side

## Runtime State Terms

Use these terms consistently:

- Active character session: `game:ac:<char_id>`, the live Redis document for a selected character. It holds current runtime state such as vitals, location, game state, symbiote, attributes, skills, and active feature refs.
- Actor snapshot/projection: `game:actor:snapshot:*`, a temporary on-demand context built for a combat scope. It is derived data and can expire.
- Character combat snapshot: a character-owned projection built by `character.combat_snapshots_requested` from `game:ac:<char_id>` plus monster runtime sources.

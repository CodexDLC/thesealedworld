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
- Redis snapshot internals not exposed by API
- temporary helper schemas used only on one side

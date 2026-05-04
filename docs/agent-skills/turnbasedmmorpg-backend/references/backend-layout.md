# Backend Layout

## Target Skeleton

```text
src/backend/
  app.py
  manage.py
  core/
  config/
  infrastructure/
  features/
    auth/
    account/
    site/
    chat/
    world/
    game_lobby/
    actor_state/
    combat/
    inventory/
    exploration/
    scenario/
    game_menu/
    arena/
```

Feature folders should use only the layers they need:

```text
api/
dto/
models/
repositories/
integrations/
services/
dependencies/
events/
workers/
runtime/
```

## Layer Responsibilities

Use `api/` for FastAPI routers and HTTP boundary code.

Use `dto/` for backend DTOs owned by the feature, unless a DTO is a shared frontend/backend API contract.

Use `models/` for SQLAlchemy ORM models owned by the feature.

Use `src/backend/infrastructure/` for low-level persistence/cache/session primitives:

- Redis managers and Redis schemas.
- DB repositories and ORM model access helpers.
- Infrastructure adapters that do not belong to one feature's business/runtime logic.

Use feature `repositories/` only for data access that is genuinely feature-local and not already represented by the infrastructure layer.

Use feature `integrations/` for facades that encapsulate low-level infrastructure managers (DB, Redis, sessions) or cross-feature boundaries behind a single cohesive interface.

Use `services/` for feature use cases and application/domain logic.

Use feature `services/` or `runtime/services/` for high-level internal feature logic. For example, a combat data service that assembles `BattleContext` from a Redis manager is a feature-internal service, while the Redis manager and Redis schema belong in `infrastructure`.

Use `dependencies/` for FastAPI dependency providers and local wiring.

Use `events/` for Redis Streams event handlers, publishers, subscribers, and stream-facing adapters.

Use `workers/` for ARQ or background jobs.

Use `runtime/` for engines, processors, assemblers, and other internal gameplay runtime code.

## Data Ownership

DB-owner / infrastructure-backed features:

- `auth`: users, credentials, refresh tokens, auth dependencies.
- `site`: public or pre-game website content, when needed.
- `chat`: rooms, messages, moderation, history.
- `world`: persistent/generated world data and world cache bootstrap.
- `game_lobby`: character list/create/delete/enter flow before active runtime.
- `character`: active character session lifecycle, `game:ac:<char_id>` repair/sync, character status, vitals, attributes, skills, and symbiote runtime data.
- `actor_state`: on-demand actor context/snapshot assembly for combat, inventory, builds, and future feature sessions. It produces temporary projections such as `game:actor:snapshot:*`; it is not the live character state source.

Runtime gameplay features:

- `combat`
- `inventory`
- `exploration`
- `scenario`
- `game_menu`
- `arena`

Runtime gameplay features should normally operate on active character sessions, temporary actor snapshots/events, and avoid direct game database access.

When a runtime feature needs Redis session data, prefer this shape:

```text
feature API/workers/processors
  -> feature service/runtime service
  -> feature integration facade when several external managers are involved
  -> src/backend/infrastructure Redis manager/schema or DB repository
```

Do not hide low-level Redis key/JSON/Lua behavior inside high-level combat/session services. Keep that behavior in an infrastructure manager or an explicit adapter that is treated as infrastructure.

Use terms precisely:

- `game:ac:<char_id>`: live active character session. This is the Redis runtime document for the selected character and contains current vitals, location, state, symbiote, attributes, skills, and active feature refs.
- `game:actor:snapshot:*`: temporary actor projection built on demand for a feature scope such as combat, inventory, build, status, or exploration. It may have a short TTL and must not be treated as source of truth.
- `actor_state` feature: the assembler/facade that builds scoped actor snapshots or context objects for other runtime systems.

## Identity Terms

Use terms consistently:

- `User` or `Account`: site account and authorization identity.
- `Character`: persistent game character owned by a user.
- `Actor`: runtime projection of a character, monster, NPC, or future entity as needed by a game subsystem. A selected player character has a live `game:ac:<char_id>` document; feature-specific actor snapshots are derived from live state and persistent data.

Login/register must not create actor state. Actor state appears only after a user enters the game with a selected character.

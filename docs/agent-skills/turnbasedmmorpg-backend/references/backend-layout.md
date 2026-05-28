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
    character/
    combat/
    inventory/
    exploration/
    scenario/
    game_menu/
    arena/
```

Feature folders should use only the layers they need. For any feature that talks to backend infrastructure, `integrations/` is the expected feature boundary for that access:

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

Use `api/` for FastAPI routers and HTTP boundary code. FastAPI inspects endpoint signatures at runtime, so router and dependency signatures must use runtime-imported annotation types. Do not put service, DTO, dependency alias, request, or response types used in `Annotated[..., Depends(...)]`, endpoint parameters, or `response_model` behind `if TYPE_CHECKING:`. If a runtime import creates a cycle, fix the feature boundary or dependency wiring; do not hide the type from FastAPI.

Use `dto/` for backend DTOs owned by the feature, unless a DTO is a shared frontend/backend API contract.

Use `models/` for SQLAlchemy ORM models owned by the feature.

Use `src/backend/infrastructure/<domain>/` for low-level domain infrastructure. Infrastructure is grouped by domain and may contain:

- `schemas/` for Redis/session/persistence schemas.
- `models/` for SQLAlchemy ORM models.
- `repositories/` for DB access helpers and persistence operations.
- `managers/` for Redis/cache/session managers.
- adapters that do not belong to one feature's business/runtime logic.

Use feature `repositories/` only for data access that is genuinely feature-local and not already represented by the infrastructure layer.

## Redis Runtime Ownership

Redis key ownership is infrastructure, not feature business logic.

Use `src/backend/infrastructure/<domain>/managers/` for Redis/cache/session managers that own key prefixes, TTLs, RedisJSON documents, locks, Lua scripts, scan patterns, serialization, delete/touch behavior, or subdocument paths.

Each Redis key-space must have exactly one owning manager. Do not split ownership of a key prefix between services, workers, event handlers, and ad hoc helpers. If a feature needs to delete, touch, scan, lock, patch, or read a Redis key, add a method to the owning manager or to the feature integration that wraps it.

For RedisJSON documents, do not make callers know stable internal paths such as `$.layout.equipment.main_hand` or `$.dirty`. The owning manager should expose methods for stable document sections and common subdocument operations. Generic `patch_fields()` is acceptable as a low-level escape hatch inside the manager boundary, but feature code should prefer semantic methods when the path is part of the domain contract.

Feature services, runtime code, API handlers, events, and workers must not build Redis keys or RedisJSON paths directly. A worker may import an infrastructure manager directly only when it is technical plumbing around that manager. If the worker applies feature rules, validation, orchestration, or cross-feature behavior, route it through a feature integration/service.

Use feature `integrations/` as the main feature-facing layer for infrastructure access. Integrations encapsulate external dependencies behind cohesive feature-level operations:

- Infrastructure Redis managers and Redis schemas.
- DB repositories and session managers from `src/backend/infrastructure/`.
- Outbound Redis Streams clients.
- Cross-feature request/reply flows.

Do not create feature persistence gateway layers that simply mirror CRUD methods from infrastructure repositories/managers. Feature integrations may depend directly on infrastructure repositories/managers, but they must expose semantic feature operations to services.

Use `services/` for feature use cases and application/domain logic.

Use feature `services/` or `runtime/services/` for high-level internal feature logic. They should describe use cases and runtime behavior, not SQL/Redis transport details. Services and runtime code call feature integrations for infrastructure work. For example, a combat data service that assembles `BattleContext` from a semantic session integration is feature-internal service logic, while the Redis manager and Redis schema belong in `infrastructure/<domain>/`.

Feature services and runtime services must not call `GameEventProducer.publish()`, `GameEventProducer.request()`, `publish_with_correlation()`, or raw reply queue operations directly. They call semantic integration methods instead, such as `notify_combat_started()`, `request_actor_snapshot()`, or `publish_round_resolved()`.

Use `dependencies/` for FastAPI dependency providers and local wiring.

Use `events/` for inbound Redis Streams event handlers and stream-facing entrypoints. **Handlers must be thin transport wrappers only** — get service/orchestrator, call one method, done. No payload parsing, no business logic, no error formatting, no reply mechanics in the handler body. The reference implementation is `src/tg_bot/features/redis/announcements/handlers/handlers.py` (3-line handlers). See `turnbasedmmorpg-redis-streams` skill for the full thin handler rule and examples.

Keep outbound Redis Streams clients under `integrations/`, for example:

```text
src/backend/features/<feature>/integrations/stream_client.py
```

The stream client owns event names, payload mapping, request/reply, correlation, timeouts, retries, reply parsing, and transport-error mapping. It should expose semantic methods to the feature integrator, not raw `publish()` calls to services.

Use `workers/` for ARQ or background jobs.

Use `runtime/` for engines, processors, assemblers, and other internal gameplay runtime code.

## Data Ownership

DB-owner / infrastructure-backed features:

- `auth`: users, credentials, refresh tokens, auth dependencies.
- `site`: public or pre-game website content, when needed.
- `chat`: rooms, messages, moderation, history.
- `world`: persistent/generated world data and world cache bootstrap.
- `game_lobby`: character list/create/delete/enter flow before active runtime.
- `character`: active character session lifecycle, `game:ac:<char_id>` repair/sync, character status, vitals, attributes, skills, symbiote runtime data, gear score recalculation, and character-owned combat snapshot assembly.

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
  -> feature integration facade
  -> src/backend/infrastructure/<domain>/ manager/schema/repository/model
```

Do not hide low-level Redis key/JSON/Lua behavior inside high-level combat/session services. Keep that behavior in an infrastructure manager or an explicit adapter that is treated as infrastructure.

Do not bypass the feature integration layer when adding infrastructure access to a feature. If the feature does not yet have `integrations/`, create it as part of the feature slice and expose semantic operations there.

Do not hide Redis Streams transport details in services/runtime code. Keep inbound stream handlers in `events/` and outbound stream clients in `integrations/`.

Use terms precisely:

- `game:ac:<char_id>`: live active character session. This is the Redis runtime document for the selected character and contains current vitals, location, state, symbiote, attributes, skills, and active feature refs.
- `game:actor:snapshot:*`: temporary actor projection built on demand for a feature scope such as combat. It may have a short TTL and must not be treated as source of truth.
- Character-owned snapshot events: `character.combat_snapshots_requested` builds combat snapshots from `game:ac:<char_id>` plus monster runtime sources.

## Identity Terms

Use terms consistently:

- `User` or `Account`: site account and authorization identity.
- `Character`: persistent game character owned by a user.
- `Actor`: runtime projection of a character, monster, NPC, or future entity as needed by a game subsystem. A selected player character has a live `game:ac:<char_id>` document; feature-specific actor snapshots are derived from live state and persistent data.

Login/register must not create runtime snapshots. Active character state appears only after a user enters the game with a selected character; combat snapshots are derived later on demand.

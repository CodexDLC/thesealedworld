# Backend Architecture Boundary Cleanup

## Status

Queued technical-debt task. This document records existing violations of the
backend architecture rules from `docs/agent-skills/turnbasedmmorpg-backend` and
`docs/agent-skills/turnbasedmmorpg-redis-streams`.

## Goal

Restore backend ownership boundaries so new feature work does not keep copying
old mixed patterns.

Required end state:

- Redis Stream handlers are thin transport wrappers.
- Cross-feature communication goes through feature integrations or Redis Streams,
  not direct imports of another feature's repositories/models.
- Redis key-space access is owned by infrastructure managers and exposed through
  semantic feature integrations.
- Workers delegate orchestration to services/integrations instead of mixing SQL,
  Redis cleanup, idempotency, and feature rules in one task body.
- CI/pre-commit has an architecture gate for the most obvious violations.

## P0 — Critical

### 1. Add backend architecture gate

Create automated checks before large cleanup work starts. At minimum catch:

- `src/backend/features/*/events/**` opening DB sessions with
  `get_session_context()`.
- `src/backend/features/*/events/**` constructing repositories/services/managers
  directly.
- direct `publish()`, `request()`, `publish_reply()`, or
  `publish_with_correlation()` outside feature `integrations/`, stream clients,
  or approved event transport wrappers.
- cross-feature imports of `src.backend.features.<other>.repositories` and
  `src.backend.features.<other>.models` outside explicitly approved integration
  modules.
- feature services/events/workers building Redis keys, RedisJSON paths, TTLs,
  locks, Lua scripts, scan patterns, or direct Redis manager ownership.

The gate must fail loudly and explain which project rule was violated.

### 2. Refactor fat Redis Stream handlers

Current violations:

- `src/backend/features/character/events/__init__.py`
- `src/backend/features/inventory/events/__init__.py`
- inspect the same pattern in `items`, `monsters`, `city_services`, `combat`,
  `scenario`, `rift`, and `loot` event modules.

Target shape:

```python
@router.on("feature.event", group="feature", reply=True)
async def on_feature_event(payload: dict[str, Any]) -> None:
    orchestrator = get_feature_event_orchestrator()
    await orchestrator.handle_feature_event(payload)
```

Handlers may extract transport fields only if unavoidable, then call one
service/orchestrator/integration method. Business logic, DB session management,
manual dependency wiring, ack/error formatting, and reply mechanics belong
outside the handler body.

## P1 — High

### 3. Move direct Redis manager construction behind integrations

Current examples:

- `src/backend/features/rift/dependencies.py`
- `src/backend/features/inventory/events/__init__.py`
- `src/backend/features/game_lobby/dependencies.py`
- `src/backend/features/combat/events/__init__.py`

Use `request.app.state.redis_managers` where this is pure dependency wiring.
Where feature behavior is involved, expose semantic operations through
`features/<feature>/integrations/`.

### 4. Replace cross-feature repository/model imports

Current examples:

- `rift` directly wires `GenerationAIService`, `MonsterGenerationRepository`,
  and `ItemInstanceRepository` in `src/backend/features/rift/dependencies.py`.
- `game_lobby` reaches into character/items/inventory repositories.
- `expedition` reaches into character/items/inventory models and repositories.
- `admin_players` reads character/items/monsters models and repositories.

Target shape:

- A feature owns its repositories/models.
- Other features call semantic integration methods or Redis Stream request/reply
  clients.
- Admin/read-only reporting may use dedicated read models or read integrations,
  not arbitrary domain repositories.

### 5. Split worker orchestration from persistence details

Current critical example:

- `src/backend/features/loot/workers/tasks/loot_claim_task.py`

The worker currently mixes payload validation, PostgreSQL transfer, Redis corpse
cleanup, idempotency, expedition handling, wallet updates, and inventory cache
invalidation. Move feature rules into service/orchestrator code and keep the ARQ
task as a thin entrypoint.

## P2 — Follow-Up

### 6. Decide document/history storage boundaries

Do not add Mongo or another document store before the architecture boundaries are
clean. Once P0/P1 are under control, evaluate document-style storage for:

- combat finalization reports and analytics traces;
- AI generation prompt/input/output/error payloads;
- chat history archives;
- rift/world/generated-content snapshots.

PostgreSQL should keep identifiers, ownership, indexes, status, and transactional
state. Redis should keep hot runtime state, buffers, sessions, streams, and
temporary projections. A document store, if added, should own large history or
append-only documents through infrastructure repositories and feature
integrations.

## Verification

- Architecture gate exists and fails on seeded violations.
- Existing backend tests pass.
- Event handler modules contain only thin transport wrappers.
- No new direct cross-feature repository/model imports appear outside approved
  integration boundaries.
- `docs/ru/backend/` and `docs/changelog/backend.md` are updated when cleanup
  changes current architecture behavior.

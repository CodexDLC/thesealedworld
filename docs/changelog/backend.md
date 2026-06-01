# Backend / Game Service Changelog

Detailed milestone history for the `src/backend` game runtime layer.

## [Unreleased]

- Starter-rift resets now rebuild hot character state from the new imprint and drop stale inventory runtime cache, while rift hearts stay out of the start-adjacent cells.

## [v0.2.0a1] - Alpha 0.2.0

- Rift backend runtime now includes portal keys, zone/session persistence, Redis managers, entry/player services, travel/event resolution, combat result integration, maintenance tools, and first scenario entry content.
- Scripted rift combat nodes now seed required `node_entry` combat events, propagate real combat outcomes, support the starter-rift `training_restart` death policy, and clear stale encounter bindings without force-applying victory.
- Combat catalog resources now include rebuilt active actions, gifts, feints, triggers, text templates, natural weapon exchanges, resistance profiles, and updated skill/modifier contracts.
- Combat resolver internals were split into explicit support modules and per-phase steps while preserving trigger/event contracts through focused tests.
- Combat runtime tuning now centralizes skill/stat formulas, actor snapshot mapping, preparation effects, feint tags, base power assembly, armor balance, equipment-derived combat power, and tunable game config.
- Combat AI now includes archetype policies, tactical memory, policy storage, offline/live-like simulation, synthetic and battle training, database-backed run reports, and ARQ worker routing.
- PvE family-pressure diagnostics now run through the live-like simulator, stay in Redis progress until completion, can enqueue one report per starter imprint, and scale player vitals by equipped armor profile.
- Redis-backed game config entries now carry admin metadata and range validation, with an audit helper for classifying future runtime tuning candidates.
- Single active-character sessions are enforced through game-session locks and frontend token flow updates.
- Automatic starter imprints now use Redis-backed least-used distribution with per-account repeat protection, and materialization preserves duplicate weapon base ids for intended dual-wield loadouts.
- Monster generation now derives skill percentages from tiered variant skill sets, tracks refreshed family resource versions for rebuild detection, and includes rebuild/backfill tooling.
- Loot TTL values are coerced to integer seconds, loot order stream handling is isolated from malformed payloads, and the dead loot-order ARQ worker was removed.

## [v0.1.0a7] - Alpha 7

- AI image text validation now uses an explicit Google GenAI SDK dependency and a dedicated Gemini client.
- Generated monster admin projections now expose member description and generated text content for cabinet inspection.
- Monster admin APIs can enqueue clan-image batches and full family visual regeneration tasks for generated monsters.
- Game lobby now exposes an internal population counter for cabinet character analytics.

## [v0.1.0a1] - First Alpha

- Backend ownership is focused on game APIs, runtime state, workers, Redis
  streams, chat/ws, game schema migrations, and game/chat persistence.
- Chat has moved into backend ownership under `src/backend/chat`, while it may
  still run as a separate process/container.
- Backend Alembic is scoped toward `game` and `chat` schemas; site auth models
  are no longer backend-owned.
- Game token helpers and route dependencies support character-scoped game
  access tokens and refresh tokens.
- Game lobby internal endpoints support site-to-game character bootstrap,
  selection, create, release, delete, and token issuance flows.
- Backend game routes enforce character ownership by user identity and character
  id rather than trusting client-provided ownership.
- Redis stream and worker boundaries are aligned around backend runtime
  ownership.
- Generation AI work now supports deterministic game-content generation flows
  for world, monster, item, and image-related tasks.
- Character combat modifier DTOs no longer expose unused attack, cast, or
  movement speed fields.
- Scenario and game-session runtime support NPC-aware dialogue handoffs,
  including the first-death respawn portal guide flow.
- Inventory runtime rebuilds by active risk run and keeps resource wallet
  projections aligned with the current expedition context.
- Backend Alembic starts from a first-alpha game/chat schema baseline; future
  schema changes should be added as follow-up revisions.

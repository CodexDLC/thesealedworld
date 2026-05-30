# Backend / Game Service Changelog

Detailed milestone history for the `src/backend` game runtime layer.

## [Unreleased]

- Redis-backed game config entries now carry admin metadata, range validation, and an audit helper for classifying future runtime tuning candidates.
- Automatic starter imprints now use Redis-backed least-used distribution with per-account repeat protection.
- Combat AI now includes archetype policies, tactical memory, offline battle simulation, and admin-triggered simulation run persistence.
- Combat runtime tuning now centralizes skill/stat formulas, actor snapshot mapping, preparation effects, feint tags, and equipment-derived combat power.
- Monster generation now derives skill percentages from tiered variant skill sets instead of family-level fixed skill values.
- Combat armor balance now treats heavy armor as a hard dodge-cap class, scales medium armor cap penalties by tier with skill recovery, and gives light armor a tier-scaled evasion bonus plus its combat skill cap boost.

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

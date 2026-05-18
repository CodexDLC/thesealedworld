# Backend / Game Service Changelog

Detailed milestone history for the `src/backend` game runtime layer.

## [Unreleased]

- Character combat modifier DTOs no longer expose unused attack, cast, or movement speed fields.

## [v0.0.0] - MVP Baseline

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

# Chat

Chat находится в backend ownership under `src/backend/chat`.

Chat может запускаться как отдельный process/container, но использует backend
codebase, settings, database/session infrastructure, Redis и Alembic model
registration.

## Ownership

Chat владеет:

- REST/chat API;
- WebSocket endpoint;
- message DTO;
- message service;
- repositories;
- `chat` schema models;
- workers/events for message archival and delivery.

Chat не является отдельной source tree с собственной копией app/config/database
слоя.

## Runtime Boundary

Chat persistence принадлежит `chat` schema, которой владеет backend Alembic.
Gameplay/system features могут публиковать chat/system events через backend
event boundaries; они не должны импортировать chat internals напрямую.

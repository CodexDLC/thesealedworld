# Rift Backend Tasks

These tasks are implementation planning notes for a future backend feature slice.

## Feature Ownership

Expected owner:

```text
src/backend/features/rift/
```

Expected layers when needed:

```text
api/
dto/
services/
runtime/
integrations/
events/
dependencies/
```

Do not wire frontend or other features directly to rift internals. Use HTTP contracts for frontend and integrations/events for backend cross-feature work.

## Data Model Draft

Potential persistent models:

- `RiftDesignTemplate`
- `RiftTemplateNode`
- `RiftInstance`
- `RiftRun`
- `RiftVisitLog`
- `RiftContract`
- `RiftMonsterFamilyRef`

Potential runtime state:

- Active run state.
- Current node.
- Discovered nodes.
- Encounter placements.
- Dirty rewards buffer.
- Core state.
- Party/raid participants.

Needs owner decision:

- Whether templates are SQL rows, JSON resources, or hybrid.
- Whether personal instances are persisted to DB or primarily Redis with a DB audit record.
- Whether first MVP needs visit history or can add it later.

## API Draft

Candidate backend endpoints:

- `GET /rift/contracts/{char_id}` - get board notices.
- `POST /rift/contracts/accept` - accept notice and create/select target.
- `GET /rift/run/{run_id}` - current run view.
- `POST /rift/run/{run_id}/enter` - enter at discovered entrance.
- `POST /rift/run/{run_id}/move` - move to connected node.
- `POST /rift/run/{run_id}/core` - handle core action.
- `POST /rift/run/{run_id}/sync` - sync dirty rewards when safe.

Needs owner decision:

- Whether board belongs under `rift`, `game_lobby`, `exploration`, or a future guild feature.
- Whether accepting a contract should immediately create an instance or only reserve parameters until travel starts.

## Integrations

Likely integrations:

- Character session integration for active feature refs and symbiote progress.
- Exploration integration for travel and encounter routing.
- Combat integration for combat-room handoff and victory result.
- Inventory/loot integration for dirty rewards.
- World integration for tier-appropriate entrance placement.
- Monsters integration for family selection and encounter composition.

Cross-feature transport should use feature integrations and Redis Streams where appropriate. Do not call other feature internals directly from rift services.

Needs owner decision:

- Whether rift travel reuses exploration directly or becomes a rift-owned travel wrapper.
- Whether combat returns to rift through a direct API response, event, or active-session state transition.

## Runtime Services

Candidate services:

- `RiftContractService`
- `RiftInstanceService`
- `RiftRunService`
- `RiftCoreService`
- `RiftRewardService`
- `RiftEncounterService`

Candidate runtime modules:

- Graph generator.
- Node resolver.
- Encounter budget builder.
- Event placement builder.
- Core action resolver.

## Persistence And Sync

Dirty loot rules:

- Rift rewards are unsynced while inside rift/unsafe route.
- Secured items are known to the AI/system.
- Dirty items are not known and cannot be restored after death unless recovered.

Needs owner decision:

- First MVP corpse recovery behavior.
- Whether dirty rewards are stored in inventory immediately with a dirty flag or kept in a rift reward buffer until sync.

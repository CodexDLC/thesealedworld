# 05. Generator Service Structure

Status: implemented as dev runtime structure.

## Goal

Split the current prototype logic into named units before it becomes too hard to change.

## Proposed Services

- `ZoneAssemblyPlanner` - selects scale/assembly preset and owns seed-based random preset choice.
- `CanvasBuilder` - builds the coordinate canvas, anchor nodes, and void-count policy.
- `NodePlacementService` - places reusable node-pool records into active canvas cells.
- `PassageGraphBuilder` - exposes the graph assembly boundary around current path/branch/blocker logic.
- `NodeEventSeeder` - seeds mandatory guard/gate events and zone-transition guard events.
- `ZoneChainBuilder` - builds prepared multi-zone chains from the same zone assembly preset.
- `RiftActionDispatcher` - routes common runtime actions: transition combat, node event, blocker resolution.

## Scope

- Keep behavior equivalent to current tests.
- Move code out of large runtime/screen functions into cohesive classes/functions.
- Avoid database work in this stage.
- Avoid changing external frontend contract unless explicitly approved.
- Do not connect AS, real combat, monster group generation, loot, or DB persistence in this stage.

## Contract Questions Before Coding

- Generator services are stateless for now.
- Seed derivation stays inside the runtime/generation layer.
- Resource lookup stays outside the generator services; services receive plain setting/preset/node-pool data.
- Frontend contract stays unchanged.

## Exit Criteria

- Same backend tests pass.
- The generation path is readable enough to add future mechanics without editing one large file.

## Implemented Module Boundaries

- `runtime/generation/planner.py`
- `runtime/generation/canvas.py`
- `runtime/generation/placement.py`
- `runtime/generation/graph.py`
- `runtime/generation/events.py`
- `runtime/generation/chain.py`
- `runtime/actions/dispatcher.py`

The old public imports remain available through `runtime/generation/__init__.py` and `runtime/navigation/__init__.py`, so services and tests do not need a contract migration.

## Still Not Part Of Stage 05

- Persistence models and migrations.
- Final `zone instance/meta` database backup layer.
- AS location/session integration.
- Real combat launch and monster-service group order.
- LLM node-pool generation.
- Final full cleanup of low-level graph helper functions into a dedicated graph implementation module.

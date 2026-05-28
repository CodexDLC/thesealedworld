# Rift Backlog

This folder is the approved working backlog for the rift feature.

Rule: each stage below is a task description, not permission to implement the next layer automatically. Before coding a stage, we first agree on its contract and runtime behavior.

## Current Order

1. [00_core_current_state.md](00_core_current_state.md) - baseline already implemented in the dev prototype.
2. [01_travel_tick_runtime.md](01_travel_tick_runtime.md) - real timed movement runtime. Implemented in the dev prototype.
3. [02_transition_combat_launch.md](02_transition_combat_launch.md) - combat interception during movement. Accepted as the closed stage-2 responsibility for the dev prototype.
4. [03_node_entry_event_resolver.md](03_node_entry_event_resolver.md) - events after entering a node. Implemented in the dev prototype.
5. [04_temporary_blocker_resolution.md](04_temporary_blocker_resolution.md) - opening temporary blockers through the common action route. Implemented in the dev prototype.
6. [05_generator_service_structure.md](05_generator_service_structure.md) - split the current prototype logic into named generator services/classes. Implemented in the dev prototype.
7. [06_persistence_models.md](06_persistence_models.md) - infrastructure Redis runtime storage and potential persistence model candidates. Implemented for Redis, DB models are not implemented yet.
8. [07_zone_instance_meta_layer.md](07_zone_instance_meta_layer.md) - final zone instance/meta ownership layer.
9. [08_llm_node_pool_generation.md](08_llm_node_pool_generation.md) - generated node pools and setting-specific descriptors.
10. [09_final_feature_refactor.md](09_final_feature_refactor.md) - final feature structure refactor after the mechanics are proven.

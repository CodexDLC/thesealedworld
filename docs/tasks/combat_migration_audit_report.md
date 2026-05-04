# Combat Temp-to-Src Migration Audit

Date: 2026-05-03

## 1. Summary

`temp/backend/domains/user_features/combat` was audited as the source of truth for combat runtime behavior. The internal RBC combat engine was restored into `src/backend/features/combat` with only import/path changes and feature-slice boundary adaptations.

Restored from `temp`:

- DTO action/actor/session/pipeline/worker/trigger contracts.
- `CombatDataService`.
- Runtime engine: ability, effects, feints, stats waterfall integration, mechanics, resolver, pipeline, target resolver, math core, victory checker.
- Runtime processors: collector, executor, AI processor, chaos service.
- ARQ worker settings and tasks.
- `CombatTurnManager` intent buffer and immediate/timeout enqueue flow.
- External dependencies imported by combat: `StatsWaterfallCalculator`, stats formulas, `modifier_dto`, `stats_enums`.

Allowed boundary differences:

- HTTP router stays in the current FastAPI feature API shape.
- Combat lifecycle keeps current Redis Streams/actor_state snapshot request boundary.
- Old `CombatManager` is represented by `src/backend/infrastructure/combat/managers/session.py` as `CombatSessionManager`.
- Frontend-facing `src/shared/schemas/combat.py` remains the current expanded DTO contract.
- `game_catalog` resource exposure remains feature-owned/public-text focused.

## 2. File-by-file audit table

| temp file | src file | status before | action taken | status after | notes |
|---|---|---:|---|---:|---|
| `api/router.py` | `api/router.py` | `OK_BOUNDARY_CHANGED` | Kept current API boundary | `OK_BOUNDARY_CHANGED` | FastAPI paths differ intentionally. |
| `orchestrators/combat_gateway.py` | `services/gateway.py` | `OK_BOUNDARY_CHANGED` | Kept thin builder boundary | `OK_BOUNDARY_CHANGED` | Dispatcher boundary replaced by feature wiring. |
| `orchestrators/combat_entry_orchestrator.py` | `services/lifecycle_service.py` + events | `OK_BOUNDARY_CHANGED` | Kept Redis Streams request boundary | `OK_BOUNDARY_CHANGED` | Monster lifecycle not guessed. |
| `orchestrators/handler/combat_session_service.py` | `services/session_service.py` | `SIMPLIFIED` | Reconnected service to restored turn manager and store compatibility | `OK_BOUNDARY_CHANGED` | Public HTTP helpers retained. |
| `orchestrators/handler/runtime/combat_turn_manager.py` | `services/turn_manager.py` | `MISSING` | Restored from temp | `OK_IMPORTS_ONLY` | Preserves intent buffer, feint consumption/return, immediate + delayed collector enqueue. |
| `orchestrators/handler/runtime/combat_view_service.py` | `services/view_service.py` | `OK_BOUNDARY_CHANGED` | Kept current expanded frontend DTO mapper | `OK_BOUNDARY_CHANGED` | Internal action/result contract not narrowed. |
| `orchestrators/handler/initialization/combat_lifecycle_service.py` | `services/lifecycle_service.py` | `OK_BOUNDARY_CHANGED` | Kept current actor_state snapshot/event boundary | `NEEDS_DECISION` | Monster snapshot contract blocks full old lifecycle restore. |
| `dto/combat_action_dto.py` | `dto/action.py` | `OK_IMPORTS_ONLY` | Restored/import-normalized | `OK_IMPORTS_ONLY` | Pair/partner move contract preserved. |
| `dto/combat_actor_dto.py` | `dto/actor.py` | `OK_IMPORTS_ONLY` | Restored/import-normalized | `OK_IMPORTS_ONLY` | Feints/status/effects/raw/stats preserved. |
| `dto/combat_arq_dto.py` | `dto/worker.py` | `OK_IMPORTS_ONLY` | Restored/import-normalized | `OK_IMPORTS_ONLY` | ARQ task payloads preserved. |
| `dto/combat_internal_dto.py` | `dto/response.py` | `MISSING` | Restored/import-normalized | `OK_IMPORTS_ONLY` | Internal response DTOs restored. |
| `dto/combat_pipeline_dto.py` | `dto/pipeline.py` | `OK_IMPORTS_ONLY` | Restored/import-normalized and exported | `OK_IMPORTS_ONLY` | Pipeline flags/mods/stages/triggers restored. |
| `dto/combat_session_dto.py` | `dto/session.py` | `OK_IMPORTS_ONLY` | Restored/import-normalized | `OK_IMPORTS_ONLY` | `pending_target_returns` and dead actor buffers preserved. |
| `dto/payloads.py` | `dto/payloads.py` | `OK_IMPORTS_ONLY` | Restored/import-normalized | `OK_IMPORTS_ONLY` | Exchange/instant payloads preserved. |
| `dto/trigger_rules_flags_dto.py` | `dto/trigger_rules.py` | `OK_IMPORTS_ONLY` | Restored/import-normalized | `OK_IMPORTS_ONLY` | Trigger DTO tree preserved. |
| `combat_engine/combat_data_service.py` | `runtime/services/data_service.py` | `SIMPLIFIED` | Restored from temp with infrastructure Redis manager | `OK_IMPORTS_ONLY` | Full context, transfer, commit, target returns restored. |
| `combat_engine/core/combat_victory_checker.py` | `runtime/engine/victory_checker.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Alive counts/end conditions restored. |
| `combat_engine/core/combat_log_builder.py` | n/a | `NEEDS_DECISION` | Audited only | `NEEDS_DECISION` | Temp file is fully commented archival code; runtime logs use event/result logs. |
| `combat_engine/core/combat_xp_manager.py` | n/a | `NEEDS_DECISION` | Audited only | `NEEDS_DECISION` | Temp file is fully commented archival code; XP final persistence remains separate. |
| `combat_engine/logic/ability_service.py` | `runtime/engine/ability_service.py` | `SIMPLIFIED` | Restored from temp; fixed path setter for current PipelineContext | `OK_IMPORTS_ONLY` | Ability costs, pipeline flags, effects, temp raw mutations restored. |
| `combat_engine/logic/effect_factory.py` | `runtime/engine/effect_factory.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Active effect factory restored. |
| `combat_engine/mechanics/feint_service.py` | `runtime/engine/feint_service.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Feint hand/token cost logic restored. |
| `combat_engine/logic/stats_engine.py` | `runtime/engine/stats_engine.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Stats waterfall restored. |
| `combat_engine/logic/mechanics_service.py` | `runtime/engine/mechanics_service.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Resource/status application restored. |
| `combat_engine/logic/combat_resolver.py` | `runtime/engine/resolver.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Accuracy/crit/evasion/parry/block/damage/control branches restored. |
| `combat_engine/logic/combat_pipeline.py` | `runtime/engine/pipeline.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Pre/stats/calc/mechanics/post flow restored. |
| `combat_engine/logic/context_builder.py` | `runtime/engine/context_builder.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Context/result initialization restored. |
| `combat_engine/logic/target_resolver.py` | `runtime/engine/target_resolver.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Target queue pairing/missing AI targets restored. |
| `combat_engine/logic/math_core.py` | `runtime/engine/math_core.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Random/check helpers restored. |
| `combat_engine/logic/chaos_service.py` | `runtime/processors/chaos_service.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Hot-join chaos flow restored behind store adapter. |
| `combat_engine/processors/collector.py` | `runtime/processors/collector.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Pair exchange, forced timeout attack, AI batch detection restored. |
| `combat_engine/processors/executor.py` | `runtime/processors/executor.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Distributed batch flow, chain waves, target returns restored. |
| `combat_engine/processors/ai_processor.py` | `runtime/processors/ai_processor.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | AI move generation restored. |
| `combat_engine/workers/combat_arq.py` | `workers/arq.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | ARQ context initialization/tasks restored. |
| `combat_engine/workers/tasks/ai_turn_task.py` | `workers/tasks/ai_turn_task.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | AI batch task flow restored. |
| `combat_engine/workers/tasks/chaos_task.py` | `workers/tasks/chaos_task.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Chaos timeout task restored. |
| `combat_engine/workers/tasks/collector_task.py` | `workers/tasks/collector_task.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Collector task and executor enqueue restored. |
| `combat_engine/workers/tasks/executor_task.py` | `workers/tasks/executor_task.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Worker lock, batch load/process/commit/finalizer enqueue restored. |
| `combat_engine/workers/tasks/victory_finalizer_task.py` | `workers/tasks/victory_finalizer_task.py` | `SIMPLIFIED` | Restored from temp | `OK_IMPORTS_ONLY` | Winner cleanup task restored. |
| `resources/game_data/abilities/**` | `features/combat/resources/abilities/**` | `OK_IMPORTS_ONLY` | Audited; facade restored | `OK_IMPORTS_ONLY` | Definitions match after import-path changes. |
| `resources/game_data/effects/**` | `features/combat/resources/effects/**` | `OK_IMPORTS_ONLY` | Audited; facade restored | `OK_IMPORTS_ONLY` | Definitions match after import-path changes. |
| `resources/game_data/feints/**` | `features/combat/resources/feints/**` | `OK_IMPORTS_ONLY` | Audited | `OK_IMPORTS_ONLY` | Definitions match after import-path changes. |
| `resources/game_data/triggers/**` | `features/combat/resources/triggers/**` | `OK_IMPORTS_ONLY` | Audited | `OK_IMPORTS_ONLY` | Rule definitions match after import-path changes. |
| `resources/game_data/gifts/**` | `features/combat/resources/gifts/**` | `OK_IMPORTS_ONLY` | Audited | `OK_IMPORTS_ONLY` | Definitions match after import-path changes. |

## 3. Restored engine logic

- Intent buffer: restored through `CombatTurnManager` and `CombatSessionStore.append_move/register_exchange_move_atomic`.
- Target queue: restored through `get_targets`, atomic exchange registration, target resolver, and commit target returns.
- Pair exchange: restored in `CombatCollector`.
- Forced timeout attack: restored in `CombatCollector` and delayed ARQ enqueue from `CombatTurnManager`.
- AI batch: restored in `AiProcessor`, collector AI requests, `ai_turn_task`, and batch move registration.
- Distributed executor lock: restored via `CombatSessionStore`/`CombatLockRepository` lock compatibility and `executor_task`.
- Target return after exchange: restored via `ctx.pending_target_returns` and `commit_battle_results`.
- Combat data service/context builder: restored in `runtime/services/data_service.py` and `runtime/engine/context_builder.py`.
- Pipeline/resolver/mechanics: restored in runtime engine modules.
- Abilities/effects/feints: restored in engine services plus resources facade.
- Stats waterfall: restored with local arithmetic evaluator replacing missing `simpleeval`.
- Logs/log builder: runtime event/result logs restored; commented temp `combat_log_builder.py` remains archival.
- Victory finalizer: restored in checker and worker task.
- ARQ tasks: restored task names and enqueue order (`combat_collector_task`, `execute_batch_task`, `ai_turn_task`, `chaos_check_task`, `victory_finalizer_task`).

## 4. Boundary changes

- API router: current HTTP endpoints retained for frontend contracts.
- Gateway/session boundary: current builder/dependency wiring retained; session service delegates move registration to restored turn manager.
- Redis Streams events: `combat.session_requested` stays the cross-feature entry; lifecycle publishes ready/failed replies.
- Redis/session manager: `CombatSessionManager` in `src/backend/infrastructure/combat/managers/session.py` exposes old `CombatManager` methods used by data service/processors/tasks.
- Game catalog resource exposure: public text catalog remains in `game_catalog`, combat runtime resources stay feature-owned.
- Frontend DTO: shared combat API DTO remains expanded; internal action/result/log DTOs were restored and not narrowed.

## 5. Remaining blockers

- Monster lifecycle is intentionally blocked. The current lifecycle can create player and shadow-player sessions, but not arbitrary monster combat actors by guessing.
- Blocked files/areas from temp: `combat_entry_orchestrator.py`, `combat_lifecycle_service.py`, chaos/hot-join only after a session exists, and any future monster team assembly.
- Required contract to continue:
  - A scoped `actor_state` monster snapshot with the same sections expected by combat: `meta`, `combat.math_model`, `combat.loadout`, `combat.skills`, `status`/`runtime.vitals`, `source`.
  - Stable ID semantics for monster actor ids versus player ids.
  - `math_model.attributes`, `math_model.modifiers`, loadout known abilities/feints, vitals, statuses, and AI flag must match `ActorSnapshot` expectations.
- Player snapshot suitability: current tests confirm player snapshots work for arena/shadow, but real-world combat should still validate live `game:ac:<char_id>` to snapshot freshness.
- Temp external dependencies moved: stats waterfall, stats formulas, modifier DTO, stats enums.
- Still missing tests: end-to-end ARQ worker execution against Redis/RedisJSON and real actor_state monster snapshot combat.

## 6. Verification

- `rg "temp\\.backend|temp/|domains\\.user_features\\.combat|resources\\.game_data|database\\.redis\\.manager\\.combat_manager|backend\\.services\\.calculators" src/backend/features/combat src/backend/core/calculators src/shared/schemas/modifier_dto.py src/shared/enums/stats_enums.py`
  - Result: no matches.
- `.\\.venv\\Scripts\\ruff.exe check src\\backend\\features\\combat src\\backend\\core\\calculators src\\shared\\schemas\\modifier_dto.py src\\shared\\enums\\stats_enums.py`
  - Result: passed.
- `.\\.venv\\Scripts\\pytest.exe tests\\backend\\features\\combat tests\\backend\\features\\game_catalog --no-cov`
  - Result: 19 passed.
- `.\\.venv\\Scripts\\pytest.exe tests\\backend\\features\\actor_state tests\\backend\\features\\arena --no-cov`
  - Result: 40 passed.

Initial sandboxed pytest attempt failed with `uv trampoline failed to spawn Python child process: permission denied`; the same commands passed after escalation.

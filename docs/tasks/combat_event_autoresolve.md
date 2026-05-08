# Combat Event Autoresolve

Date: 2026-05-08

## Status

Future implementation task. This is a product and architecture note, not a final design decision.

## Context

Exploration can generate PvE events where the player meets weak enemies. For enemies that are clearly below the character's power, forcing the player into a full manual combat loop creates friction: the player wants the reward and consequence of fighting, but not the repeated interaction cost.

The intended product behavior is similar to auto combat in Heroes of Might and Magic III: when the matchup is heavily favorable, show an autoresolve option on the event itself.

This is not an LLM feature. It is deterministic machine combat using existing combat math.

## Goal

Add an event-level PvE autoresolve path for weak encounters:

1. Exploration creates or loads an encounter event.
2. Backend estimates player advantage from gear score, monster threat, level, tier, or similar combat inputs.
3. If the advantage is high enough, the event UI may show an `Autoresolve` action.
4. On click, backend resolves the battle in memory without opening manual combat UI.
5. Backend applies only the final consequences: HP/EN/resource deltas, defeated enemies, XP/reward context, loot, and event outcome.

## Non-Goals

- Do not use LLMs for combat decisions.
- Do not store full combat logs for event autoresolve.
- Do not create a full interactive Redis combat session for every autoresolved exchange.
- Do not duplicate combat math outside the combat feature.
- Do not replace manual combat; this is an optional shortcut for favorable PvE events.

## Proposed Flow

```text
exploration encounter event
 -> estimate autoresolve eligibility
 -> player clicks Autoresolve
 -> exploration requests combat event autoresolve
 -> combat builds in-memory BattleContext from player + monster ActorSnapshot data
 -> autoresolve runner loops exchange batches in memory
 -> runner returns normalized result aggregate
 -> exploration applies result, XP, rewards, and event transition
```

## Combat Ownership

The implementation should live inside the combat feature as an in-memory runtime mode:

```text
src/backend/features/combat/runtime/autoresolve/
  runner.py
  policy.py
  targeting.py
  result.py
```

Expected responsibilities:

- `runner.py`: owns the round loop, max-round guard, seed, and final result.
- `policy.py`: chooses actions for actors: initially basic attack, later optional feint/ability policy.
- `targeting.py`: manages target selection for 1v1, 1vN, and NvN encounters.
- `result.py`: defines a small result/aggregate contract for callers.

The autoresolve runtime should reuse existing combat engine/executor logic where practical, especially `CombatExecutor`, `CombatPipeline`, `ActorSnapshot`, `CombatActionDTO`, and `ExchangePayload`.

## Cross-Feature Boundary

Exploration should not import combat runtime internals directly.

Use a combat-owned service/integration/event boundary so exploration can ask for:

```text
resolve this encounter with these actor snapshots and constraints
```

and receive:

```text
final consequences and reward/XP aggregate
```

Exact transport can be decided during implementation. If this crosses feature ownership asynchronously, use Redis Streams according to the project event-bus rules. If it remains a direct backend feature dependency, expose a semantic combat integration/service rather than reaching into `runtime/autoresolve`.

## Eligibility Heuristic

Initial eligibility can be conservative:

- Compute player combat power from gear score and/or existing combat stats.
- Compute enemy combat power from monster level, tier, threat, combat profile, and count.
- Show autoresolve only when player advantage is clearly high.

Example direction:

```text
player_power >= enemy_power * 2.5
and enemy_threat_total below configured threshold
and encounter is PvE/non-boss/non-script-critical
```

Open tuning parameters:

- gear-score ratio threshold;
- enemy level/tier gap;
- total enemy count multiplier;
- elite/boss flags that disable autoresolve;
- minimum remaining player HP/EN required;
- probability or expected damage warning shown to the player.

## Runtime Rules

The first version can be intentionally simple:

- All living actors select an exchange action each round.
- Targeting selects the next living opposing target or the weakest living target.
- Player policy uses basic attack by default.
- Monster policy uses basic attack by default.
- Optional feint auto-use can be added if the actor has feints in hand and enough tokens.
- Abilities can be added later through a controlled policy allowlist.
- Stop on victory, defeat, or `max_rounds`.

Required safety controls:

- deterministic `seed` for reproducibility;
- hard `max_rounds`;
- no per-round Redis writes;
- no full combat log persistence;
- clear stopped reason: `victory`, `defeat`, `max_rounds`, or `error`.

## Result Contract

Autoresolve should return a thin result, not a detailed session log.

Minimum fields:

```text
winner_team
rounds
stopped_reason
seed
player_survived
player_hp_before
player_hp_after
player_en_before
player_en_after
defeated_enemy_ids
damage_dealt_by_player
damage_taken_by_player
kills_by_player
rounds_survived
enemy_threat_total
enemy_level_total
used_abilities
used_feints
```

If normal combat already produces an XP/reward aggregate in a compatible shape, autoresolve should populate that same shape and call the same finalization path. The autoresolve runner should not own XP math.

## Persistence

Autoresolve should not persist each exchange. It should commit only final consequences:

- update active character HP/EN and relevant temporary state;
- mark encounter/event outcome;
- award XP/rewards through existing finalizers;
- optionally store compact audit/debug metadata: seed, encounter id, enemy ids, winner, rounds, stopped reason.

Full combat logs, turn-by-turn event lists, and analytics history are not required for this mode unless a future product requirement asks for them.

## UX Notes

The event UI can show an autoresolve button only when the backend marks the event as eligible.

Suggested player-facing behavior:

- `Fight manually`: opens normal combat.
- `Autoresolve`: resolves weak encounter immediately.
- If autoresolve reaches `max_rounds` or cannot safely resolve, return a clear event outcome and offer manual combat if the encounter remains valid.

The UI should avoid implying guaranteed safety unless the backend result model actually guarantees it.

## Open Decisions

- Exact power formula for player advantage.
- Whether autoresolve is synchronous in the request or queued as one background task.
- Whether exploration calls combat via direct integration or Redis Streams request/reply.
- Whether compact debug metadata is stored permanently or only in logs.
- Whether used feints/abilities are enabled in MVP or deferred.
- How to handle partial failure after combat resolves but before rewards/state are committed.

## Acceptance Notes

A future implementation is acceptable when:

- exploration can mark weak PvE events as autoresolve-eligible;
- autoresolve uses combat-owned in-memory runtime code;
- combat math is reused rather than duplicated;
- no per-exchange Redis combat session writes are required;
- a deterministic seed and max-round guard exist;
- result data is sufficient for existing XP/reward finalization;
- manual combat remains available for normal or dangerous encounters;
- tests cover 1v1, 1vN, max-round stop, player defeat, player victory, and XP/reward aggregate mapping.

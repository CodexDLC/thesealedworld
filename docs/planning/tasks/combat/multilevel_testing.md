# Combat Multilevel Testing

Status: expected.

Combat migration and monster actor integration are considered implemented. The
remaining work is to finish verification across test levels.

## Scope

Cover combat behavior from isolated runtime logic to realistic player-facing
flows:

- unit tests for deterministic runtime services and calculators;
- integration tests for combat session state, actor snapshots, Redis/RedisJSON,
  ARQ workers, and cross-feature boundaries;
- frontend/API contract tests for combat actions and dashboard payloads;
- E2E smoke flows for entering combat, submitting actions, resolving exchanges,
  finishing combat, and returning to the game surface.

## Backend Unit Coverage

- [ ] Resolver/pipeline edge cases.
- [ ] Ability and effect processing.
- [ ] Feint hand/token cost behavior.
- [ ] Trigger activation and trigger text lookup.
- [ ] Actor snapshot stat recalculation.
- [ ] Combat result aggregation.

## Backend Integration Coverage

- [ ] Player vs generated monster combat actor snapshots.
- [ ] Combat session lifecycle against Redis/RedisJSON.
- [ ] Collector/executor/AI/victory-finalizer ARQ task flow.
- [ ] Active character snapshot freshness.
- [ ] Combat finalization and state commit.
- [ ] Combat reward/XP handoff where applicable.

## Frontend/API Coverage

- [ ] Combat dashboard payload contains required hero, target, action, log, and
      status data.
- [ ] Manual combat action submission returns expected fragments or payloads.
- [ ] Failed/invalid actions produce clear UI-safe errors.
- [ ] Combat completion returns the player to the correct game surface.

## E2E Smoke Coverage

- [ ] Start or enter a PvE combat.
- [ ] Submit one or more player actions.
- [ ] Let enemy/AI actions resolve.
- [ ] Finish combat with player victory.
- [ ] Verify state after combat: vitals, rewards, logs/result summary, and active
      game surface.

## Non-Goals

- Do not reopen the old temp-to-src migration audit.
- Do not rebuild monster lifecycle from old temp code.
- Do not add new combat mechanics only to satisfy tests.

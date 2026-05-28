# Combat Skill Runtime Reference

Status: reviewed against current combat and character runtime surfaces.

This file records which combat skill effects are currently backed by runtime
code and which remain design direction.

## Current Runtime Sources

```text
src/backend/features/character/runtime/combat_math_model.py
src/backend/features/character/runtime/combat_actor_input.py
src/backend/features/combat/runtime/engine/context_builder.py
src/backend/features/combat/runtime/engine/resolver.py
src/backend/features/combat/runtime/services/experience_finalizer.py
src/backend/features/game_catalog/combat/resources/
```

Related active-action taxonomy:

```text
docs/game-design/rules/combat/active_actions.md
```

## Implemented Or Runtime-Backed

- Weapon mastery keys are part of actor snapshots and item/combat skill
  contracts.
- Tactical style keys are part of actor snapshots. `skill_dual_wield` has an
  off-hand exchange and trigger resources.
- `skill_light_armor` can raise the effective dodge cap for light armor in the
  character combat math model.
- `skill_medium_armor` can recover the medium armor dodge-cap penalty in the
  character combat math model.
- Heavy chest armor applies a hard dodge-cap layer; `skill_heavy_armor` is used
  by resolver-side heavy armor logic.
- `skill_parrying` is wired into combat stats, block/parry resolution and
  defense experience.
- `skill_anatomy` and `skill_tactics` receive combat progression from combat
  result power in the experience finalizer.
- Feint availability references `skill_tactics`, `skill_light_armor`,
  `skill_parrying`, `skill_anatomy`, and `skill_dual_wield`.

## Design Direction Not Yet Full Runtime Canon

- Weapon mastery as a complete item-trigger unlock layer.
- Ranged combat perfect backstep is wired as a pre-evasion style trigger with a
  25% cap; the full ranged feint tree is still future design work.
- Full two-handed Ignore model beyond current style hooks.
- Full shield mastery economy beyond existing shield guard/block/reflection
  direction.
- Full anatomy healing/regeneration model.
- Full tactics anti-evasion, counter and tactical-overwhelm model.
- Full non-combat skill gameplay for crafting, gathering, survival, trade and
  leadership.

## Monster Boundary

Monsters can carry skill values and overrides, but the player-facing library
should describe skills from the player perspective.

Monster skill contracts and overrides belong in developer docs and stable
runtime docs under `docs/ru` once the monster/combat domain is reviewed.

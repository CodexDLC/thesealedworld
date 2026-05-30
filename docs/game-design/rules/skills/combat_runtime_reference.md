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
- Weapon mastery damage assembly uses two body stats per weapon class. Strength
  and agility feed ordinary weapon damage; endurance is not part of weapon
  damage and is reserved for survival or style-specific mechanics.
- Tactical style keys are part of actor snapshots. `skill_dual_wield` has an
  off-hand exchange and trigger resources.
- `skill_shield_mastery` scales shield block events. A successful shield block
  is not a full damage cancel: it rolls a shield profile branch. Defensive
  branches add `shield_guard_power` to mitigation for that hit; counter
  branches return shield power as reflected damage.
- Shield formula flags can temporarily change the branch math for feints and
  prepared reactions: `force_shield_defense_branch`,
  `force_shield_counter_branch`, `shield_branch_invert`, and
  `shield_counter_from_absorbed`. Numeric pipeline modifiers can scale
  `shield_block_chance_mult`, `shield_guard_power_mult`, and
  `shield_counter_power_mult`.
- Shield tactical preparations now use those shield formula mutations:
  active/full/absolute defense force the defensive shield branch, while
  aggressive defense forces the counter branch and reflects from shield contact.
- Shield base items define `shield_block_chance`,
  `shield_block_defense_weight`, and `shield_block_counter_weight`. Small
  shields have higher event chance and weaker power; heavy shields have lower
  event chance and stronger defensive power.
- `skill_light_armor` can raise the effective dodge cap for light armor in the
  character combat math model.
- `skill_medium_armor` can recover the medium armor dodge-cap penalty in the
  character combat math model.
- Heavy chest armor applies a hard dodge-cap layer; `skill_heavy_armor` is used
  by resolver-side heavy armor logic.
- `skill_parrying` is wired into parry resolution and defense experience. It no
  longer scales shield block chance.
- `skill_anatomy` and `skill_tactics` receive combat progression from combat
  result power in the experience finalizer.
- Feint availability references `skill_tactics`, `skill_light_armor`,
  `skill_parrying`, `skill_anatomy`, and `skill_dual_wield`.
- Weapon and tactical feint catalogs can expose mass-target techniques through
  `target=ALL_ENEMIES`, `target_count`, and `secondary_damage_mult`. Runtime
  treats the primary target as the exchange target and resolves secondary
  targets as costless one-way physical hits from the same action.

## Design Direction Not Yet Full Runtime Canon

- Weapon mastery as a complete item-trigger unlock layer.
- Ranged combat perfect backstep is wired as a pre-evasion style trigger with a
  25% cap. Ranged combat also has a tactical multi-target covering volley; the
  broader ranged tree remains design work.
- Full two-handed style economy beyond current parry/block pressure hooks.
- Full shield mastery economy beyond existing shield guard/block/reflection and
  endurance/strength guard-power scaling.
- Full anatomy healing/regeneration model.
- Full tactics anti-evasion, counter and tactical-overwhelm model.
- Full non-combat skill gameplay for crafting, gathering, survival, trade and
  leadership.

## Monster Boundary

Monsters can carry skill values and overrides, but the player-facing library
should describe skills from the player perspective.

Monster skill contracts and overrides belong in developer docs and stable
runtime docs under `docs/ru` once the monster/combat domain is reviewed.

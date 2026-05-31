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
- Weapon mastery damage assembly uses normalized Strength/Agility/Endurance
  weights per weapon class. Endurance replaces part of the old
  Strength/Agility share instead of adding extra damage above the class budget.
- Tactical style keys are part of actor snapshots. `skill_dual_wield` has an
  off-hand exchange and trigger resources.
- Archery/ranged combat disables passive armor counter openings on defense:
  light armor dodge and medium armor parry do not open a counter by themselves.
  Feints and prepared reactions can still open the counter window, and if they
  do, light armor's counter-chance multiplier remains active.
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
  character combat math model. A successful dodge in light armor opens the
  normal counter-check window; light armor skill can also multiply that
  counter chance when the light-armor bonus roll passes.
- `skill_medium_armor` can recover the medium armor dodge-cap penalty in the
  character combat math model. Medium armor does not open counters on dodge;
  after a successful parry it opens the counter-check window only through the
  `skill_medium_armor` roll.
- Heavy chest armor applies a hard dodge-cap layer. `skill_heavy_armor`
  amplifies the Endurance-derived natural `physical_resistance` by up to 50%
  at full mastery; for example, 30% natural resistance becomes 45%. Heavy armor
  does not open the normal armor counter window and still has resolver-side
  subsequent-hit chain protection.
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

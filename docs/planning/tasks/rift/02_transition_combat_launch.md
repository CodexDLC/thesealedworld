# 02. Transition Combat Launch

Status: accepted / implemented as dev placeholder.

## Goal

When a transition tick resolves `combat`, backend launches or requests a combat encounter instead of completing movement.

## Scope

- Use travel tick result to decide `none/combat`.
- On `combat`, freeze or interrupt active travel.
- Create the integration point to combat/encounter services.
- Return a screen state that tells frontend to switch to combat.

## Accepted Responsibility

This stage owns only the chance and interruption contract for combat during travel.

- Transition combat is rolled only while moving into a new ordinary node.
- Return travel into visited nodes does not roll transition combat.
- Target nodes with guaranteed/scripted combat suppress transition combat completely.
- If transition combat happens, active travel is interrupted and must not silently complete.
- The current dev placeholder can resolve combat as `victory` and then complete travel into `to_node_id`.
- After transition combat resolves, `last_travel.suppress_random_node_combat` tells the future node-entry resolver not to roll a random combat immediately in the destination node.
- Transition combat descriptive text is selected from setting/master `encounter_vocabulary.transition_combat`.
- Base chance per tick belongs to setting/master `transition_combat_rules.base_chance_per_tick`; current accepted prototype value is `0.35`.
- Future skill influence is represented only as `opening_context` contract data for combat assembly.

This stage does not own the real monster group generation formula, boss encounter templates, node-entry event rolls, combat buffs/debuffs, or final combat service integration.

## Out Of Scope

- Node entry events.
- Chest/trap/resource/special events.
- Monster family generation redesign.
- Boss/key-room combat formulas.
- Skill-to-combat-effect resolution.

## Contract Questions Before Coding

- Deferred: real combat start will later use the standard combat/group assembly mechanism.
- Resolved for dev placeholder: after `victory`, player continues into `to_node_id`.
- Resolved for dev placeholder: frontend receives `combat_prompt`, then calls combat resolve and swaps in returned `screen`.

## Future Integration Notes

- Ordinary transition combat should request a standard monster group by player tier/gear score budget.
- Opening context can later bias initiative/position/first exchanges, but it must not change the basic chance that transition combat happens.
- Boss/key encounters should be handled as node/scripted encounters and may pass richer group templates or budget overrides into the monster group generator.
- The same opening-context contract should be reusable by future open-world travel combat.

## Exit Criteria

- Transition combat is distinguishable from node-entry combat.
- Travel runtime cannot silently complete while combat is active.
- The stage is considered closed for the dev prototype when chance, suppression rules, placeholder resolve, and future opening-context metadata are present.

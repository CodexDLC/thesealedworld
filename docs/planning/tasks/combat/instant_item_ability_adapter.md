# Combat Instant Item Ability Adapter

Date: 2026-05-07

## Status

Near-term dependent implementation task. This should be started after the core
combat ability logic is designed and implemented well enough for item actions to
delegate to abilities instead of duplicating combat math.

The exact item combat contract should be revisited when combat item instances are implemented in detail, especially around targeting, consumption, logging, and whether any item-specific damage stats are still needed.

## Context

Current combat accepts `use_item` actions and maps them to `CombatMoveDTO(strategy="item")`, but the runtime does not yet resolve the item instance into combat behavior.

Observed current behavior:

- `use_item` creates a move with `strategy="item"` and `InstantPayload(item_id=...)`.
- `ContextBuilder` only marks the source type as `item`.
- `AbilityService` does not process `item_id`; it only processes `ability_id` / `feint_id`.
- `CombatResolver` does not currently select `item_damage_base`, `item_damage_spread`, `item_accuracy`, or `item_crit_chance` for `source_type="item"`.
- `ActorStats.mods` receives item modifier fields only from the actor raw math model defaults or from pre-existing `actor.raw.modifiers`, not from the selected instant item.

This means instant items currently exist as an intent/DTO path, not as a complete combat mechanic.

## Intended Direction

Instant combat items should initially be modeled as item instances that reference ability ids.

An item instance may own player-facing and log-facing data, while the actual combat action is delegated to the referenced ability:

- item instance fields: title, description, inventory identity, stack/quantity, text for combat logs, optional usage metadata.
- action resource: `ability_id` or equivalent ability reference stored in item mechanics/data.
- ability config: target rules, effects, raw mutations, override damage, pipeline mutations, triggers, and resource effects.

In this model, the item is a presentation, ownership, and inventory wrapper around an ability-powered combat action.

## Proposed Runtime Shape

Add a small item action adapter before ability processing, or as a narrow service called by the combat pipeline.

Possible flow:

1. Detect `move.strategy == "item"`.
2. Read `payload.item_id`.
3. Resolve the item from `source.loadout.belt` or another approved combat item source.
4. Read the ability reference from the item instance, for example `ability_id`, `mechanics.ability_id`, or `mechanics.abilities[0]`.
5. Build an effective instant action for the ability path.
6. Call or reuse `AbilityService` behavior with the resolved ability id.
7. Attach item-facing metadata to result events/log context.
8. Mark the item for consumption only after the action is accepted and applied.

The adapter should keep item lookup, item metadata, and inventory consumption separate from ability math.

## Parameters To Consider

Item instances may need usage parameters in addition to ability id:

- ability id / action id.
- target mode override, if the item needs stricter targeting than the ability default.
- effect power, duration, stack count, quality, rarity, or roll parameters.
- log title and text variants for use, hit, miss, heal, buff, debuff, expire, and consume.
- whether the item is consumed on cast, on hit, or always after the action is accepted.
- whether stack decrement happens immediately or during combat result commit.
- whether the item can be used from belt only or also from other quick-access containers.
- whether the item can pass additional params into `EffectFactory` / ability effects.

## Open Decisions

- Canonical field name for the ability reference on item instances.
- Whether instant item combat data lives in item `mechanics`, generated instance metadata, or a dedicated combat-use block.
- Whether item log text should extend combat catalog descriptions or remain item-instance text.
- Whether consumable item usage should be committed by combat runtime, inventory integration, or a post-result session commit step.
- Whether throwable/offensive items should use ability `override_damage` only, or also support resolver-level `item_damage_*` stats.
- Whether `CombatResolver._get_offensive_val()` should support `source_type="item"` at all if ability delegation covers most instant item cases.

## Acceptance Notes

A future implementation should make `use_item(item_id)` do more than set `source_type="item"`:

- the item must resolve to a concrete ability/action;
- missing, unusable, or malformed item references must produce a clear skip/failure reason;
- item title/description/log text should be available to combat logs or result events;
- item consumption rules should be explicit and testable;
- the design must be verified against actual combat item instance schemas before finalizing.

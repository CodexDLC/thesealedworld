# Item Catalog Content Expansion

Status: expected.

The MVP item resource and generation refactor is considered implemented. The
remaining item work is content expansion: base item catalog depth, consumables,
and combat-usable item actions.

## Goals

- Add a broader set of base weapons, armor, tools, and utility items.
- Add consumables that can later participate in combat through the combat item
  action / ability path.
- Add deterministic names, descriptions, tags, and material compatibility for
  low-tier/common items.
- Keep item source data separated into base, material, affixes, sockets/future
  sources, and generated narrative metadata.

## Base Item Catalog

- [ ] Expand base weapons by weapon type and early-game tier.
- [ ] Expand base armor by armor class and slot.
- [ ] Add shields, belts, tools, and simple utility bases where the current
      gameplay loop needs them.
- [ ] Add tags that support loot, generation, UI filtering, and future crafting.
- [ ] Add tests that new base ids load, validate, and can be generated.

## Consumables

- [ ] Define first combat consumable categories: healing, stamina/energy,
      thrown damage, status cleanse, simple buffs/debuffs.
- [ ] Decide which consumables are usable only from belt/quick slots.
- [ ] Link combat consumables to ability/action ids after core ability logic is
      ready.
- [ ] Define consumption rules: on accepted use, on hit, always, or commit-time.
- [ ] Add player-facing names/descriptions and combat-log text hooks.

## Combat Integration Dependency

Combat consumables depend on the near-term task:

```text
docs/planning/tasks/combat/instant_item_ability_adapter.md
```

Do not duplicate combat math in item resources. Combat items should delegate to
the combat ability/action path where practical.

## Non-Goals

- Do not reopen the MVP item resource refactor.
- Do not bring back old flat `bonuses` as canonical item source data.
- Do not add full crafting/sockets/gems before their own design task starts.

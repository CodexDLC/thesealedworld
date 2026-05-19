# Post-MVP Crafting and Field Utility

## Status

Post-MVP design note. Do not implement this as a one-off recipe or temporary action before the general crafting engine exists.

## Goal

Define the future boundary between full city crafting and limited expedition utility.

The intended crafting direction is a hybrid of:

- WoW-style profession recipe menus.
- EVE-style material chains, stations, and economy pressure.
- Lineage-style progression, master NPCs, and meaningful craft hubs.

This document records the direction only. It is not an MVP implementation task.

## Core Boundary

Full crafting belongs to city and settlement infrastructure.

Expeditions should not expose full production. Expedition actions may support survival and equipment upkeep, but must not become a parallel crafting system.

## City Crafting

City crafting should eventually provide:

- A crafting district or workshop services.
- Master NPCs/trainers for learning professions and recipes.
- Stations and benches required by recipe type.
- Recipe lists grouped by profession.
- Batch crafting where appropriate.
- Material requirements and outputs.
- Skill progression through the shared skill progression model.
- Quality, tier, and optional success/variance formulas.

Expected stations:

- Forge/anvil for `skill_weapon_craft` and heavy metal work.
- Armor bench for `skill_armor_craft`.
- Jewelry bench for `skill_jewelry_craft`.
- Alchemy table for `skill_alchemy`.
- Engineering workbench for `skill_engineering`.
- Artifact focus for `skill_artifact_craft`.
- Medical/tailoring table for advanced `skill_first_aid` recipes.

## Expedition Utility

Expedition utility is intentionally narrow:

- First Aid: field medicine, bandages, wound treatment, later poison/bleed support.
- Field repair: rough emergency repair for weapons and armor.

Allowed expedition actions:

- Use an existing bandage or medical consumable.
- Create a primitive bandage only if the future crafting engine supports field recipes cleanly.
- Roughly repair durability or reduce a broken-item penalty.

Disallowed expedition actions:

- Full equipment creation.
- Full profession recipe books.
- Station-grade crafting.
- Large batch production.
- Economy-grade refining chains.

## First Aid

`skill_first_aid` is the first likely bridge between field utility and full crafting.

Design intent:

- In the field: simple medicine, bandages, emergency treatment.
- In the city: better medical recipes, antiseptics, antidotes, stimulant kits, regeneration kits.

First Aid should remain resource-based. It should not become free healing from nothing.

Possible early recipes after the crafting engine exists:

- `dirty_bandage`: consumes low-tier cloth/rags.
- `field_bandage`: consumes plant fiber or cleaner cloth.
- `antiseptic_bandage`: consumes cloth plus herbal/alchemy material.
- `anti_poison_kit`: consumes herbs/reagents.

Skill effects to consider later:

- Healing item potency.
- Bandage cooldown reduction.
- Bleed mitigation or cleanse support.
- Poison mitigation or cleanse support.
- Medical recipe tier unlocks.

## Field Repair

Field repair is a separate utility loop, not full item crafting.

Potential links:

- `skill_weapon_craft`: rough weapon repair.
- `skill_armor_craft`: rough armor repair.
- `skill_engineering`: repair tools, traps, or devices later.

Field repair should:

- Restore limited durability.
- Reduce temporary broken-item penalties.
- Consume repair materials or kits.
- Be weaker than station repair.

Field repair should not:

- Create new weapons or armor.
- Add affixes.
- Perform full upgrades.
- Replace city workshops.

## Future Crafting Engine

Do not implement crafting as hard-coded service actions. Build a reusable engine first.

Expected backend pieces:

- `CraftingRecipeDTO`
- `CraftingRecipeRegistry`
- `CraftingService`
- Inventory integration for input consumption and output creation.
- Skill progression integration via `SkillProgressionCalculator`.
- Station/tool/trainer requirement checks.
- `CraftResultDTO` for success, outputs, consumed materials, skill rewards, and messages.

Expected recipe fields:

- `recipe_id`
- `profession_skill`
- `required_skill`
- `inputs`
- `outputs`
- `craft_time`
- `station_requirements`
- `tool_requirements`
- `trainer_or_unlock_requirements`
- `quality_formula`
- `xp_action_power`

## Skill Scope

Crafting skills reserved for the future city crafting engine:

- `skill_first_aid`
- `skill_weapon_craft`
- `skill_armor_craft`
- `skill_jewelry_craft`
- `skill_alchemy`
- `skill_engineering`
- `skill_artifact_craft`

Gathering and resource cleanup should feed this system later:

- Low-tier junk and scraps can become useful inputs.
- Inventory clutter should be solved by recycling/crafting loops, not by deleting items through one-off cleanup actions.

## Explicit Non-Goals For MVP

- No full crafting UI now.
- No temporary hard-coded bandage recipe now.
- No full repair system now.
- No crafting economy balancing now.
- No trainer/station implementation now.

## First Future Slice

When this becomes active, the recommended first slice is:

1. City crafting service surface with one trainer/workbench.
2. Recipe registry with one or two First Aid recipes.
3. Inventory input/output transaction.
4. Skill XP reward through the shared progression calculator.
5. Minimal recipe list UI.
6. Focused tests for recipe validation, consumption, output, and XP.

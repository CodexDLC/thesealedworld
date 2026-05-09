# Item Resource / Generation Refactor Notes

This is a living note for the item-generation refactor. Keep decisions here when they become stable enough that future context compaction should not lose them.

## Status

MVP item-resource refactor is closed unless playtests expose a blocker. This file remains as an archived decision reference for code and agent skills.

Post-MVP development now lives in:

```text
docs/game-design/roadmap/item_resources_post_mvp.md
```

## Fixed Decisions

- Item display should be split into two conceptual blocks:
  - **Base**: base item identity plus material identity.
  - **Bonuses**: rolled affixes and bundle affixes.
- `implicit_bonuses` are base item identity. They explain why one base item differs from another.
- If material bonuses are added later, they are base-block data, not affixes. MVP target keeps material as multiplier/tags/name/slots only.
- Affixes should be stored separately as compact source data on the item instance.
- Item instance affixes store rolled facts: `affix_id`, `value`, source/roll metadata. They do not duplicate technical/descriptive catalog fields.
- Affix technical meaning and UI text are catalog-owned. This lets a catalog fix rename/remap `crit_chance_add` into trigger chance semantics across existing items while preserving each item's rolled number.
- Do not use old flat `bonuses` as source of truth in the target model. If a compiled projection is needed for compatibility, it should be built at actor assembly time, not persisted as the canonical item data.
- Bundles do not own separate math values. A bundle is a template containing keys of single affix definitions.
- Two-slot bundle files from the old prototype are not the target model. New bundles should mostly be 4-affix templates. Three-affix bundles are only valid for containers that can hold exactly/at most 3 affixes.
- Boss/world-entity artifacts can force fixed bundles, unique pools, tags, triggers, or narrative source data.
- Do not bend the new item model around the current actor builder limitations. If needed, refactor actor assembly and UI projection to consume the new source structure cleanly.
- Future sockets/gems should be a separate top-level source key, not mixed into affixes or base bonuses.

## Core Multipliers

There is no separate `affix_grade_mult` in the target model.

The material tier multiplier is the single tier/grade scale:

```text
tier_mult
```

It comes from the selected material definition. Material type and material tier decide the multiplier in the material catalog.

It is used in three different places:

```text
base item value = base item value * tier_mult
durability = base durability * tier_mult
internal/base parameters = internal/base parameters * tier_mult where that parameter is numeric and tier-scaled
affix step base = affix base value * tier_mult
```

This is intentional. The same material scale strengthens base item power, durability, internal/base numeric parameters, and the affix step base, but those are separate parts of the final item.

Do not also multiply mechanical power by rarity/default grade multipliers. The current prototype still has `rarity.default_mult`; target model should keep rarity/item grade for labels and container rules, while material `tier_mult` is the mechanical multiplier.

Affix value target model:

```text
affix_step_base = affix_base * tier_mult
affix_value = sum(random_step(affix_step_base) for _ in GLOBAL_AFFIX_STEPS)
```

`GLOBAL_AFFIX_STEPS = 5` for the first implementation. It is a global balance lever and should later move to server/admin settings after generation tests. Step roll ranges are another balance lever.

Step roll range is not one global value for every stat. Each single-affix catalog entry should define its own roll profile because percentages, flat values, and attributes need different variance and rounding.

Target roll profile fields:

```text
roll_profile = {
    "step_spread": 0.05,      # each step rolls 0.95..1.05 around affix_step_base
    "rounding": "decimal",   # decimal | floor_int | round_int
    "round_digits": 4,
}
```

Rules:

- Percentage/probability affixes should usually keep small spread and decimal rounding.
- Flat combat/resource/environment values can use wider spread when that stat wants visible item variance.
- Attribute affixes should use integer rounding, usually `floor_int`, so a roll never silently gives more than its visible threshold.
- The affix catalog owns the roll profile. Item instances store the final rolled value and compact roll metadata, not the whole profile.
- Bundle math does not override this. Bundles reference single affixes, and each referenced affix keeps its own roll profile.

## Material Model

Loot service should choose material from monster/location/source grade and pass `material_id` to the generator.

Material should provide:

- `tier`
- `tier_mult`
- allowed item categories/types
- optional allowed armor classes
- material tags
- `slots` as future crafting/gem/socket capacity after MVP
- optional stat or affix-pool bias later

Do not add direct material bonuses in the MVP target model. Material identity comes from `tier_mult`, name/prefix, tags, color/description, and future `slots`.

If material bonuses are added later, they belong in the base block:

```text
Base = base item power + base item implicit bonuses + material multiplier + material bonuses
Bonuses = affixes
```

Examples:

- Leather armor can favor evasion / heat / nature-style defense.
- Metal armor can favor armor / block / durability and may apply evasion penalties.
- Cloth can favor environment, magic, status, or garment utility.
- Wood can favor shields, bows, staffs, nature, guard, or accuracy.

## Generation Pipeline

Target generation stages:

1. Choose base item.
2. Choose material in loot service and pass `material_id` to item generator.
3. Apply `tier_mult` from material to base item values:
   - power
   - durability
   - base/internal parameters
   - base item implicit bonuses
4. Keep material tags/name/prefix/source data for UI and AI narrative enrichment.
5. Build affix container from item tier/grade/source rules:
   - min/max affix count
   - allowed affix pools
   - max affix grade if we keep a separate grade label later
   - bundle chance
   - allowed bundle sizes
6. Choose fill strategy:
   - random single affixes
   - 4-affix bundle
   - 3-affix bundle only for 3-affix containers
   - boss/artifact forced bundle
   - bundle plus random filler
7. Resolve each affix id through the single-affix definition catalog.
8. Roll each affix value using:
   - affix base value
   - material/item `tier_mult`
   - global step count
   - step roll range
9. Store source data:
   - base data
   - material data
   - `affixes[]`
   - roll breakdown
   - source tags
   - seed
10. Build any combat-facing projection at runtime for the mapper. Do not persist old flat `bonuses` as item source of truth.
11. Send base tags, material tags, affix tags, bundle tags, monster/location/source tags to AI narrative enrichment.

Tier 0/common trash items should not request LLM text. They need deterministic fallback names and descriptions from base item + material/base tags. LLM enrichment starts only above the configured tier threshold or for explicitly forced narrative sources.

## Data Shape Target

Source of truth should eventually look like:

```python
mechanics = {
    "implicit_bonuses": {...},        # base item identity
    "material": {
        "material_id": "mat_iron_ingot",
        "tier_mult": 1.5,
        "tags": ["iron", "heavy", "reliable"],
    },
    "affixes": [
        {
            "affix_id": "weapon_accuracy",
            "source": "bundle:duelist_4",
            "value": 0.04,
            "roll_quality": 0.82,
            "roll": {"step_roll_total": 1.13},
        }
    ],
    "sockets": [],                    # future gems/socket inserts
}
```

Combat mapper should preserve source separation where possible:

```text
item:{id}:base
item:{id}:material:{material_id}
item:{id}:affix:{affix_id}
item:{id}:socket:{socket_id}
```

Target actor assembly should be pluggable by top-level mechanics key instead of hardcoding one merged bonus blob. Conceptually:

```python
ITEM_MECHANIC_APPLIERS = {
    "implicit_bonuses": apply_base_bonuses,
    "material": apply_material_source,
    "affixes": apply_affix_sources,
    "sockets": apply_socket_sources,
}
```

Adding a new source type should usually mean adding one top-level key and one applier function, not rewriting the whole actor builder.

Affix application should resolve `affix_id` through the affix catalog:

```text
item.affixes[].affix_id -> catalog.technical.target + catalog.technical.operation
item.affixes[].value -> operation value applied to actor math
```

UI should resolve the same `affix_id` through catalog descriptive data:

```text
item.affixes[].affix_id -> catalog.descriptive.display_name / ui_template
item.affixes[].value -> formatted value in template
```

## Affix Catalog Target

Affix catalog entries should follow the same split used by combat resources:

```text
technical = how it works
descriptive = how it is shown/narrated
```

Single affix definition should include:

- `id`
- `target_field`
- operation (`add`, `mult`, `set`, `cap_add`, final list TBD)
- `base_value`
- value kind / formatter hint
- roll profile:
  - step spread
  - rounding mode
  - round digits
- `pool`
- `allowed_item_types`
- optional allowed slots / armor classes
- tags
- min tier / item grade rules if needed
- descriptive display name and UI template

Affix definitions should be grouped by gameplay influence, not by item type. Item type and slot restrictions belong in pool/mapping files.

Target resource layout:

```text
src/backend/features/items/resources/affixes/
  definitions/
    combat_offense.py
    combat_defense.py
    combat_control.py
    combat_resource.py
    world_exploration.py
    world_survival.py
    crafting.py
    economy.py
    attributes.py
    utility.py
  bundles/
    bundles_3.py
    bundles_4.py
  pools.py
  catalog.py
  schemas.py
```

Rules:

- Do not create one bundle file per style such as `duelist.py` or `bulwark.py`.
- Bundle files are grouped by bundle size: `bundles_3.py`, `bundles_4.py`.
- Bundle entries are named style templates inside those files, for example `duelist_4`, `bulwark_4`, `survival_3`.
- `pools.py` maps item types, slots, classes, tags, and future source constraints to allowed single-affix ids.
- World/non-combat affixes are first-class. They may later feed active character/world-check modifiers instead of combat-only stats.

Example pool direction:

```python
AFFIX_POOLS_BY_ITEM_TYPE = {
    "weapon": ["weapon_accuracy", "weapon_penetration", "crit_chance"],
    "shield": ["block", "shield_guard_power", "parry", "armor"],
    "armor": ["armor", "physical_resistance", "evasion"],
    "garment": ["environment_heat_resistance", "environment_cold_resistance", "travel_comfort"],
    "accessory": ["attribute_strength", "attribute_perception", "luck", "magical_resistance"],
    "belt": ["inventory_cell_capacity", "quick_slot_capacity", "carry_weight"],
}

AFFIX_POOLS_BY_SLOT = {
    "main_hand": ["weapon_accuracy", "weapon_penetration", "crit_chance"],
    "off_hand": ["block", "parry", "shield_guard_power"],
    "body": ["armor", "physical_resistance"],
    "feet": ["evasion", "travel_speed"],
    "ring": ["attributes", "magic_resistance"],
}
```

Example world/non-combat affixes:

```text
travel_speed
scouting_bonus
pathfinding_bonus
environment_cold_resistance
resource_find_chance
crafting_speed
trade_bonus
```

Bundle definition should include:

- `id`
- `affix_ids` as references to single affix definitions
- allowed item types
- min tier / item grade
- tags
- source/resource requirements

## Loot Direction

Loot source grade should drive material/item tier roughly as:

```text
drop item grade = monster/location grade +/- 1
```

Bosses/elites can have better offsets or forced artifact templates.

Crafting is out of scope for this refactor plan. The only generator-level decision is that the final generator should be reusable by any source. Loot and future crafting can both pass resolved generation inputs, but crafting rules themselves will be more complex and should not be designed here.

For this document, focus on the generator contract:

```text
resolved base_id + resolved material_id + source tags + generation constraints
-> shared item generation pipeline
```

## Open Questions

- Exact per-affix roll profiles for the real catalog entries. The model is fixed: roll profile lives on the single-affix definition.
- Affix grade decision is fixed for now: no separate affix grade. Material tier drives affix strength through `tier_mult`.
- Which player modifiers are allowed as affixes.
- Final allowed affix pools per item type.
- How much material bias affects affix pools versus only base-block bonuses.
- Whether material bonuses ever return after MVP, or material remains multiplier/tags/slots only.
- Whether item affix instances should store only `affix_id + value`, or also a tiny `operation_snapshot` for safety. Current preference: catalog-owned operation, no snapshot.
- Exact operation semantics for multiplicative affixes: whether `value=0.05` compiles to `*1.05`, and how this is represented in raw stat operations.
- Whether catalog technical changes should always be retroactive for old items. Current preference: yes for semantics/display, no for rolled numeric value.
- Where runtime compiled projections live after removing persistent old `bonuses`.
- How reroll/upgrading works for:
  - value reroll
  - affix replacement
  - bundle replacement
  - locked affixes
  - material replacement

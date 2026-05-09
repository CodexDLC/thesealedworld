---
name: turnbasedmmorpg-item-resources
description: Item resource and generation rules for TurnBasedMMORPG. Use when creating, refactoring, reviewing, or generating item bases, materials, affixes, bundles, item generation, item text AI payloads, sockets, item-to-actor projection, or loot/craft inputs for items.
---

# TurnBasedMMORPG Item Resources

## First Reads

Read these before changing item resources or generation:

- `docs/agent-skills/turnbasedmmorpg-project/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-backend/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-combat-contract/SKILL.md` when item stats touch combat actor math
- `docs/tasks/item_resource_refactor_notes.md`
- `src/backend/features/items/resources`
- `src/backend/features/items/runtime/item_factory.py`
- `src/backend/features/character/runtime/combat_math_model.py`
- `src/backend/core/calculators/stats_waterfall_calculator.py`

## Current Phase

This project is pre-alpha. Prefer clean target design over compatibility layers. Do not add legacy fallbacks, dual systems, or soft migration scaffolding unless the user explicitly asks.

## Core Rules

- Treat `docs/tasks/item_resource_refactor_notes.md` as the living reference for item-resource decisions.
- Base item semantics and modifier contracts are different layers.
- Base/implicit item data does not need an `operation`. The actor/item mapper interprets it by item type, slot, tags, and specific key.
- Affixes, buffs, debuffs, feints, abilities, passives, sockets, and gems must use a shared modifier contract when they change numeric actor/world values.
- Modifier contracts compile to the existing waterfall command language: `+x`, `-x`, `*x`, `=x`.
- `StatsWaterfallCalculator` already parses command strings and builds formulas. Use it; do not invent a second math language.
- If a modifier contract entry lacks an operation, treat it as invalid catalog data. Only base/implicit item semantics may omit operation.

## Material And Scaling

- Material `tier_mult` is the single mechanical grade-scale.
- Material type and material tier define `tier_mult` in the material catalog.
- Apply material `tier_mult` to:
  - base power
  - durability
  - numeric internal/base parameters that are tier-scaled
  - affix step base
- Do not multiply mechanical item power by rarity/default grade multipliers. Rarity/grade controls label, affix container rules, and generation constraints, not a second mechanical scale.
- Do not add direct material stat bonuses for the MVP target. Material identity is multiplier, tags, name/prefix, color/description, and future sockets.

## Affix Resources

Group affix definitions by gameplay influence, not by item type:

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

- Do not create one file per style such as `duelist.py` or `bulwark.py`.
- Bundles are grouped by size only: `bundles_3.py` and `bundles_4.py`.
- Bundles contain references to single affix ids and own no separate math values.
- `pools.py` maps item type, slot, class, tags, and future source constraints to allowed single-affix ids.
- World/non-combat affixes are first-class and may later feed active-character/world-check modifiers.

## Item Source Shape

Target item mechanics source of truth:

```python
mechanics = {
    "implicit_bonuses": {...},
    "material": {"material_id": "...", "tier_mult": 1.5, "tags": [...]},
    "affixes": [
        {"affix_id": "weapon_accuracy", "value": 0.04, "source": "bundle:duelist_4", "roll": {...}}
    ],
    "sockets": [],
}
```

- Do not persist old flat `bonuses` as the canonical item data.
- If a compiled projection is needed, build it at actor assembly/runtime projection time.
- Preserve source separation where possible: `item:{id}:base`, `item:{id}:material:{material_id}`, `item:{id}:affix:{affix_id}`, `item:{id}:socket:{socket_id}`.
- Add future mechanics as top-level source keys with one applier function each.

## Text Generation

- Tier 0/common trash items must not request LLM text.
- Tier 0 needs deterministic names/descriptions from base item, material, and tags.
- LLM enrichment starts only above the configured threshold or for explicitly forced narrative sources such as boss/artifact/quest/world-entity.
- The project already uses AI prompt routers. Put stable style rules in the system message and compact per-item data in the user payload.
- Structured output should be provider/schema-driven where supported; script validation belongs in code, not in model self-check fields.

## Verification

Run the strongest practical targeted checks for changed surfaces. Common checks:

```powershell
.\.venv\Scripts\pytest.exe tests\backend\features\items --no-cov
.\.venv\Scripts\pytest.exe tests\backend\features\character\runtime --no-cov
.\.venv\Scripts\pytest.exe tests\backend\features\combat --no-cov
git diff --check
```

If `git diff --check` reports pre-existing generated/static whitespace outside the touched item files, report it and do not rewrite unrelated files.

# Item Model Reference

Status: technical design reference for the current item resource model.

Code sources:

- `src/backend/features/items/resources/`
- `src/backend/features/items/runtime/item_factory.py`
- `src/backend/features/items/services/catalog_service.py`
- `src/backend/features/items/services/generation_service.py`
- `src/backend/features/items/dto/`
- `tests/backend/features/items/`

## Ownership

The active item model is owned by `src/backend/features/items`.

Design docs may explain the model and future direction, but they must not
duplicate the full item catalog or act as a field-level schema source. The
runtime catalog, DTOs, tests, and resource definitions are the source of truth.

## Current Shape

Generated item mechanics are built from separated sources:

- base item;
- material;
- item grade / rarity tier;
- implicit bonuses;
- affixes;
- reserved future sockets;
- generation and narrative metadata.

The old flat `bonuses` map is not the canonical item storage shape. Runtime
projection may still expose compact bonus maps for consumers, but source data
should remain separated.

## Base Item

The base item defines the item identity:

- id;
- display name and text;
- type;
- slot;
- allowed materials;
- base power or defensive value;
- damage spread where relevant;
- implicit bonuses;
- related skill where relevant;
- tags and category metadata.

Base item resources currently live under:

```text
src/backend/features/items/resources/base_item/
```

Base item content expansion is tracked separately in:

```text
docs/planning/tasks/item_catalog_content_expansion.md
```

## Material And Tier

Materials provide `tier_mult` and material identity.

Current material families include ingots, woods, leathers, cloths, and parts.
The material multiplier can scale item power and generated affix values.

Examples of material source files:

```text
src/backend/features/items/resources/material/ingots.py
src/backend/features/items/resources/material/woods.py
src/backend/features/items/resources/material/leathers.py
src/backend/features/items/resources/material/cloths.py
```

## Grade And Rarity

Rarity tier maps to item grade through the current item grade configuration.

Current behavior to preserve:

- common / tier-0 starter items can have no affixes;
- item grade controls the affix container and labels;
- grade should not be treated as a second direct power multiplier unless a
  future task explicitly redesigns that rule;
- high grade items can unlock more affixes and AI text eligibility.

## Implicit Bonuses

`implicit_bonuses` are base item properties. They belong to the item source
shape and can be projected into combat or world systems.

Examples:

- weapon accuracy penalties, crit profile, and small weapon parry profile;
- shield block chance and parrying off-hand profile;
- armor penalties such as evasion, anti-dodge, accuracy, or resource penalties;
- jewelry type profile bonuses; jewelry `base_power` maps to flat
  `magic_armor`;
- garment anchor/environment profile bonuses such as cold, heat, gravity, or
  bio resistance;
- environmental resistance;
- quick-slot capacity;
- concentration/stamina regen.

Implicit bonuses are not random affixes. They are part of the item identity.

Combat base-item implicit rules:

- armor pieces carry armor value plus penalties; they do not grant offensive
  bonuses;
- main-hand weapons can carry crit chance, weapon parry chance, damage spread,
  and accuracy/evasion penalties;
- off-hand parrying weapons can carry a higher parry baseline than ordinary
  weapons, paid for by their own penalties;
- shields keep their shield block baseline, also paid for by accuracy/evasion
  penalties;
- rings, earrings, and amulets use `base_power` as flat magical armor. Their
  implicit bonuses are slot profiles, not affix duplicates: ring currently
  carries `mental_resistance`, amulet carries `debuff_avoidance`, and earring
  carries `initiative`;
- garments use implicit bonuses as their anchor/environment protection layer:
  cold, heat, gravity, and bio resistance come from garment identity. Garment
  `base_power` does not become physical armor or jewelry-style magical armor.
  Future garment-only affix pools may add combat elemental resistances, but
  those affixes are not part of the current baseline;
- always-on armor bypass, resistance suppression, or bleed scaling should live
  in triggers, feints, affixes, or future active mechanics instead of baseline
  weapon implicit bonuses.

## Affixes

Affixes are generated modifier additions.

The current affix system includes:

- affix definitions;
- affix pools;
- modifier contracts;
- affix bundles;
- value rolls;
- tier/step scaling.

Affix values can scale with material tier multiplier and roll configuration.
The exact roll behavior belongs to runtime code and tests, not this design
document.

Code roots:

```text
src/backend/features/items/resources/affixes/
src/backend/features/items/resources/modifier_contracts/
```

## Sockets

Sockets are reserved future item mechanics.

Do not implement full sockets, gems, or inserts from this reference alone. They
need a separate design and implementation task before becoming runtime truth.

## Runtime Projection

The item system can produce compact runtime projections for consumers such as
monster generation and combat actor assembly.

Runtime projection may expose:

- item id;
- owner key;
- base id;
- slot;
- combat power;
- combat bonuses;
- related skill;
- generation context;
- affix summary.

Projection is a consumer-facing view. It should not replace the separated
source model.

## Player Text

Common and low-tier deterministic items can use deterministic text without AI.
AI text is reserved for cases where grade, source, or future artifact rules
justify it.

Generated narrative metadata must not own mechanics. Mechanics are validated and
compiled by code.

## Future Work

Future item work should be split into concrete tasks:

- base item catalog expansion;
- consumables;
- crafting foundation;
- sockets and inserts;
- affix reroll and replacement;
- artifact and boss item identity;
- world modifiers;
- magic, vampiric, and elemental affixes;
- world-aware item text and history.

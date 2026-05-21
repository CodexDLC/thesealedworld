# Attributes Technical Reference

This document records the current runtime mapping between primary attributes and
derived combat values.

Status: implementation reference plus design notes.

Current code sources:

- `src/backend/features/character/runtime/rules/attribute_modifiers.py`
- `src/backend/features/character/runtime/rules/vital_constants.py`
- `src/backend/core/calculators/stats_waterfall_calculator.py`
- `src/backend/core/calculators/data/attribute_rule_profiles.py`
- `src/backend/features/monsters/runtime/combat_math_model.py`

## Attribute Keys

Player and monster actors use the same primary attribute keys:

| Node | Attribute | Runtime key |
| --- | --- | --- |
| Body | Strength | `strength` |
| Body | Agility | `agility` |
| Body | Endurance | `endurance` |
| Core | Intellect | `intellect` |
| Core | Memory | `memory` |
| Core | Mental | `mental` |
| Sensor | Perception | `perception` |
| Sensor | Projection | `projection` |
| Sensor | Prediction | `prediction` |

## Waterfall Flow

The current runtime flow is:

1. Actor snapshot provides raw attributes and raw modifiers.
2. `StatsWaterfallCalculator` calculates final primary attributes.
3. The selected `attribute_profile` derives secondary modifier commands from
   primary attributes.
4. Derived values are combined with raw modifier base/source/temp values.

Primary attributes are stored as raw layered values:

```json
{
  "base": 10,
  "source": {},
  "temp": {}
}
```

Secondary modifiers use the same base/source/temp shape, then the waterfall
evaluates additive, multiplicative, divisive, and set commands.

## Player Attribute Profile

The player profile uses `ATTRIBUTE_MODIFIER_RULES`.

### Body Node

| Attribute | Runtime output | Formula |
| --- | --- | --- |
| `strength` | `physical_damage` | `strength * 1.0` |
| `strength` | `physical_suppression` | `strength * 0.02` |
| `agility` | `evasion` | `agility * 0.05` |
| `agility` | `initiative` | `agility * 0.5` |
| `endurance` | `physical_resistance` | `endurance * 0.02` |
| `endurance` | `poison_resistance` | `endurance * 0.02` |
| `endurance` | `bleed_resistance` | `endurance * 0.02` |
| `endurance` | `environment_bio_resistance` | `endurance * 0.02` |

Vitals:

| Runtime output | Formula |
| --- | --- |
| `hp` | `(strength + agility + endurance) / 3 * 4` |
| `hp_regen` | `(strength + agility + endurance) / 3 * 0.1` |

Implementation note: runtime stores this as per-attribute constants:
`HP_PER_BODY_ATTRIBUTE = 4 / 3` and `HP_REGEN_PER_BODY_ATTRIBUTE = 0.1 / 3`.

### Core Node

| Attribute | Runtime output | Formula |
| --- | --- | --- |
| `intellect` | `magical_damage` | `intellect * 1.0` |
| `intellect` | `magical_penetration` | `intellect * 0.02` |
| `memory` + `prediction` | `counter_attack_chance` | `memory * 0.0025 + prediction * 0.0015` |
| `mental` | `magic_resist` | `mental * 0.02` |
| `mental` | `control_resistance` | `mental * 0.02` |
| `mental` | `mental_resistance` | `mental * 0.02` |
| `mental` | elemental resistances | `mental * 0.02` |

Energy:

| Runtime output | Formula |
| --- | --- |
| `en` | `(intellect + memory + mental) / 3 * 2` |
| `en_regen` | `(intellect + memory + mental) / 3 * 0.5` |

Elemental resistances currently derived from `mental`:

- `fire_resistance`
- `water_resistance`
- `air_resistance`
- `earth_resistance`
- `light_resistance`
- `dark_resistance`
- `arcane_resistance`
- `nature_resistance`

### Sensor Node

| Attribute | Runtime output | Formula |
| --- | --- | --- |
| `perception` | `anti_dodge_chance` | `perception * 0.03` |
| `perception` + `projection` + `prediction` | `stamina` | `(perception + projection + prediction) / 3 * 10` |
| `perception` + `projection` + `prediction` | `stamina_regen` | `1 + (perception + projection + prediction) * 0.1` |

Naming note: the player-facing design name is **Concentration**. The current
runtime field is `stamina`. Rename/migration is future work if the code adopts
the new terminology.

## Current Simplifications

Strength and Intellect currently grant `1.0` damage output per attribute point.
The earlier design wording says `1-2` damage per point, but runtime currently
uses the simple `1.0` coefficient. A more complex formula can be designed later.

## Player-Only Library Boundary

The player library article should describe only the player-facing meaning of
attributes. It should not describe monster profile overrides, size modifiers,
raw snapshot structure, or code paths.

## Monster Attribute Profiles

Monsters use the same primary attribute keys but may use different runtime
profiles.

Current profiles:

- `player`
- `monster:humanoid`
- `monster:beast`

Current monster profile behavior:

- `monster:humanoid` and `monster:beast` use the same rules today.
- Monster profiles remove player `hp_regen` derivation.
- Monster HP is derived as `endurance * 4`.
- Other attribute-to-modifier rules are inherited from the player profile unless
  later overridden.

This means player HP uses the Body node average, while monster HP currently uses
Endurance only.

## Monster Size Layer

Monster combat math also applies size-based source modifiers after the base
character-style raw model is built.

| Size | Source modifiers |
| --- | --- |
| `small` | `evasion +0.05`, `physical_resistance -0.02`, `damage_mult *0.9` |
| `medium` | no extra size modifiers |
| `large` | `hp +20`, `evasion -0.03`, `physical_resistance +0.03`, `damage_mult *1.1` |
| `huge` | `hp +50`, `evasion -0.06`, `physical_resistance +0.06`, `damage_mult *1.25` |

Default monster size by role:

| Role | Default size |
| --- | --- |
| `minion` | `small` |
| `veteran` | `medium` |
| `elite` | `large` |
| `boss` | `huge` |

Explicit monster metadata can override the default size class.

## Future Or Non-Runtime Ideas

The old attributes document contains ideas that are not current runtime
formulas:

- carry weight;
- active construct limit;
- global XP gain from Memory;
- social influence;
- illusions;
- crafting quality;
- loot luck;
- critical accuracy mini-crit rule.

These can become future design tasks or system-specific formulas, but they are
not current attribute runtime truth.

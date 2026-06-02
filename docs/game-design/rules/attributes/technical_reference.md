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
   effective primary attributes.
4. Derived values are combined with raw modifier base/source/temp values.
5. Combat stats assembly converts weapon power plus weighted stat power into the
   final hand damage base.

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

All attribute-derived outputs use the same effective-attribute curve before the
profile coefficient is applied:

```text
effective(stat) = stat * stat / 11
```

### Body Node

| Attribute | Runtime output | Formula |
| --- | --- | --- |
| `strength` | `physical_strength_power` | `effective(strength) * 1.0` |
| `strength` | `physical_suppression` | `effective(strength) * 0.02` |
| `agility` | `physical_agility_power` | `effective(agility) * 1.0` |
| `agility` | `evasion` | `effective(agility) * 0.02` |
| `agility` | `initiative` | `effective(agility) * 0.5` |
| `endurance` | `physical_endurance_power` | `effective(endurance) * 1.0` |
| `endurance` | `physical_resistance` | `effective(endurance) * 0.02` |
| `endurance` | `poison_resistance` | `effective(endurance) * 0.02` |
| `endurance` | `bleed_resistance` | `effective(endurance) * 0.02` |
| `endurance` | `environment_bio_resistance` | `effective(endurance) * 0.02` |

Vitals:

| Runtime output | Formula |
| --- | --- |
| `hp` | `effective(endurance) * 3.0` |
| `hp_regen` | `effective(endurance) * 0.1` |

Heavy chest armor can add a skill source on top of the Endurance-derived
`physical_resistance`: `effective(endurance) * 0.02 * skill_heavy_armor *
0.50`. This is an amplification of natural body resistance, not a flat +50
percentage points.

### Core Node

| Attribute | Runtime output | Formula |
| --- | --- | --- |
| `intellect` | `magical_damage` | `effective(intellect) * 1.0` |
| `intellect` | `magical_penetration` | `effective(intellect) * 0.02` |
| `memory` + `prediction` | `counter_attack_chance` | `effective(memory) * 0.0025 + effective(prediction) * 0.0015` |
| `mental` | `magic_resist` | `effective(mental) * 0.02` |
| `mental` | `control_resistance` | `effective(mental) * 0.02` |
| `mental` | `mental_resistance` | `effective(mental) * 0.02` |
| `mental` | elemental resistances | `effective(mental) * 0.02` |

Energy:

| Runtime output | Formula |
| --- | --- |
| `en` | `effective(mental) * 1.25` |
| `en_regen` | `effective(mental) * 0.25` |

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
| `perception` | `anti_dodge_chance` | `effective(perception) * 0.03` |
| `projection` | `stamina` | `effective(projection) * 2.7` |
| `projection` | `stamina_regen` | `1 + effective(projection) * 0.1` |

Naming note: the player-facing design name is **Concentration**. The current
runtime field is `stamina`. Rename/migration is future work if the code adopts
the new terminology.

## Current Simplifications

Strength, Agility, and Endurance grant `1.0` physical power per effective
attribute point. Ordinary weapon damage uses class-specific normalized weights
across Strength and Agility only; Endurance stays available for survival and
style-specific mechanics. Weapon mastery gates only the stat-derived part of
weapon damage. Weapon item power itself is not reduced by mastery.

Current base-power assembly:

```text
stat_raw = strength_power * class_strength_weight
         + agility_power * class_agility_weight
mastery_factor = 0.25 + 0.75 * weapon_mastery
stat_effective = stat_raw * mastery_factor
hand_damage_base = weapon_power + stat_effective
```

Intellect still grants `1.0` magical damage output per attribute point.

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
- Monster HP is derived as `effective(endurance) * 3`.
- Other attribute-to-modifier rules are inherited from the player profile unless
  later overridden.

This means player and monster HP both use Endurance only; monster profiles remove
player `hp_regen`.

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

# Modifier Vocabulary

Status: current vocabulary reference for reviewed modifier names.

This document uses the active modifier field names from
`src/backend/features/character/dto/modifiers.py`. Older names such as
`hp_max`, `energy_max`, `dodge_chance`, `parry_chance`,
`shield_block_chance`, `damage_reduction_flat`, `magical_resistance`, and
`magical_damage_base` are legacy aliases or old design names.

## Vitals

| Field | Meaning |
| --- | --- |
| `hp` | Maximum health derived into actor vitals. |
| `hp_regen` | Health regeneration. |
| `en` | Maximum Energy. |
| `en_regen` | Energy regeneration. |
| `stamina` | Current runtime field for the future player-facing Concentration resource. |
| `stamina_regen` | Stamina / Concentration regeneration. |
| `resource_cost_reduction` | Reserved resource cost reduction modifier. |
| `initiative` | Initiative / reaction ordering bonus. |

## Main Hand

| Field | Meaning |
| --- | --- |
| `main_hand_damage_base` | Final main-hand or two-handed strike base after weapon power plus mastered stat power. For unarmed actors, Strength can be mapped here directly. |
| `main_hand_damage_spread` | Final main-hand damage variance after mastery stabilization. |
| `main_hand_damage_bonus` | Reserved extra main-hand damage bonus. |
| `main_hand_weapon_power` | Trace value: weapon/item power before stat power is added. |
| `main_hand_stat_damage_raw` | Trace value: weighted Strength/Agility/Endurance power before mastery gating. |
| `main_hand_stat_damage_effective` | Trace value: stat damage actually added after mastery gating. |
| `main_hand_mastery_factor` | Trace value: normalized mastery factor applied to stat damage. |
| `main_hand_damage_spread_raw` | Trace value: damage variance before mastery stabilization. |
| `main_hand_armor_penetration_pct` | Percent armor penetration from the main hand. |
| `main_hand_armor_ignore_chance` | Chance to ignore armor from the main hand. |
| `main_hand_accuracy` | Main-hand accuracy modifier. The built-in `0.70` hit baseline lives in the resolver, not here. |
| `main_hand_crit_chance` | Main-hand crit / trigger chance. |
| `main_hand_crit_cap` | Main-hand crit cap. Current DTO default: `0.75`. |

## Off Hand

| Field | Meaning |
| --- | --- |
| `off_hand_damage_base` | Final off-hand weapon strike base after weapon power plus mastered stat power. |
| `off_hand_damage_spread` | Final off-hand damage variance after mastery stabilization. |
| `off_hand_damage_bonus` | Reserved extra off-hand damage bonus. |
| `off_hand_weapon_power` | Trace value: weapon/item power before stat power is added. |
| `off_hand_stat_damage_raw` | Trace value: weighted Strength/Agility/Endurance power before mastery gating. |
| `off_hand_stat_damage_effective` | Trace value: stat damage actually added after mastery gating. |
| `off_hand_mastery_factor` | Trace value: normalized mastery factor applied to stat damage. |
| `off_hand_damage_spread_raw` | Trace value: damage variance before mastery stabilization. |
| `off_hand_armor_penetration_pct` | Percent armor penetration from the off hand. |
| `off_hand_armor_ignore_chance` | Chance to ignore armor from the off hand. |
| `off_hand_accuracy` | Off-hand accuracy modifier. |
| `off_hand_crit_chance` | Off-hand crit / trigger chance. |
| `off_hand_crit_cap` | Off-hand crit cap. Current DTO default: `0.75`. |

## Combat Item

These fields are reserved for combat consumables, throwables, scrolls, and
similar instant item actions.

| Field | Meaning |
| --- | --- |
| `item_damage_base` | Item action damage base. |
| `item_damage_spread` | Item action damage variance. |
| `item_damage_bonus` | Reserved item action damage bonus. |
| `item_armor_penetration_pct` | Item action armor penetration. |
| `item_armor_ignore_chance` | Item action armor ignore chance. |
| `item_accuracy` | Item action accuracy modifier. |
| `item_crit_chance` | Item action crit / trigger chance. |
| `item_crit_cap` | Item action crit cap. Current DTO default: `0.75`. |

## Global Physical

| Field | Meaning |
| --- | --- |
| `physical_damage` | Legacy/reserved flat physical damage field. Weapon attacks no longer add this automatically. |
| `physical_strength_power` | Attribute-derived Strength power used by weapon and style assembly. |
| `physical_agility_power` | Attribute-derived Agility power used by weapon assembly. |
| `physical_endurance_power` | Attribute-derived Endurance power used by survival and style-specific assembly, not ordinary weapon damage. |
| `physical_damage_bonus` | Additional global physical damage bonus. |
| `accuracy` | Global accuracy modifier added to relevant offensive branches. |
| `physical_suppression` | Physical resistance suppression, currently from Strength. |
| `armor_penetration_pct` | Global percent armor penetration. |
| `armor_penetration_flat` | Global flat armor penetration. |
| `armor_ignore_chance` | Global armor ignore chance. |
| `crit_chance` | Global physical crit / trigger chance bonus. |
| `crit_power` | Reserved critical effect power. |

## Magical

| Field | Meaning |
| --- | --- |
| `magical_damage` | Magical damage base, currently derived from Intellect. |
| `magical_damage_spread` | Magical damage variance. |
| `magical_damage_bonus` | Reserved magical damage bonus. |
| `magical_accuracy` | Magical accuracy modifier. |
| `magical_damage_power` | Reserved magical damage multiplier/power. |
| `magical_penetration` | Magical / elemental penetration, currently derived from Intellect. |
| `spell_land_chance` | Spell/debuff land chance; reserved or only partially consumed. |
| `magical_crit_chance` | Magical crit chance. |
| `magical_crit_cap` | Magical crit cap. Current DTO default: `0.75`. |

## Active Defense

| Field | Meaning |
| --- | --- |
| `evasion` | Dodge/evasion chance before cap and anti-evasion. |
| `dodge_cap` | Evasion hard cap. Current default: `0.75`. |
| `anti_dodge_chance` | Attacker anti-evasion / tracing modifier. |
| `parry` | Weapon parry chance supplied by equipment or effects. |
| `parry_cap` | Parry hard cap. Current default: `0.50`. |
| `block` | Shield block chance. |
| `shield_block_cap` | Shield block hard cap. Current default: `0.75`. |

## Mitigation And Shield

| Field | Meaning |
| --- | --- |
| `physical_resistance` | Percent physical resistance. |
| `magic_resist` | Percent magical resistance. |
| `resistance_cap` | Resistance cap. Current default: `0.85`; verify consumer before relying on it. |
| `armor` | Flat physical damage reduction from armor. |
| `magic_armor` | Flat elemental/magical damage reduction from jewelry power. |
| `shield_guard_power` | Shield guard power for the current shield model. |
| `shield_absorb_ratio` | Shield absorb ratio. Current default: `0.40`. |
| `shield_reflect_ratio` | Shield reflect ratio. Current default: `1.00`. |

## Elemental

Elemental keys follow the school names used by Gifts:

- `fire_damage_bonus`, `fire_resistance`
- `water_damage_bonus`, `water_resistance`
- `air_damage_bonus`, `air_resistance`
- `earth_damage_bonus`, `earth_resistance`
- `light_damage_bonus`, `light_resistance`
- `dark_damage_bonus`, `dark_resistance`
- `arcane_damage_bonus`, `arcane_resistance`
- `nature_damage_bonus`, `nature_resistance`

Elemental resistance is currently derived from `mental` through the attribute
bridge. Elemental damage bonuses are reserved until corresponding combat
systems consume them.

## Status And Bio

| Field | Meaning |
| --- | --- |
| `control_chance_bonus` | Chance bonus for applying control effects. |
| `control_resistance` | Resistance to control. |
| `mental_resistance` | Resistance to mental effects. |
| `debuff_avoidance` | Chance or rating for avoiding debuffs. |
| `shock_resistance` | Reserved shock resistance. |
| `poison_damage_bonus` | Reserved poison damage bonus. |
| `poison_resistance` | Poison resistance, currently derived from Endurance. |
| `poison_efficiency` | Reserved poison application efficiency. |
| `bleed_damage_bonus` | Reserved bleed damage bonus. |
| `bleed_resistance` | Bleed resistance, currently derived from Endurance. |

## Special

| Field | Meaning |
| --- | --- |
| `counter_attack_chance` | Counter-attack chance, currently from Memory and Prediction. |
| `counter_attack_cap` | Counter-attack cap. Current default: `0.50`. |
| `vampiric_power` | Reserved vampiric healing power. |
| `vampiric_trigger_chance` | Reserved vampiric trigger chance. |
| `vampiric_trigger_cap` | Reserved vampiric trigger cap. Current default: `1.0`. |
| `healing_power` | Reserved outgoing healing power. |
| `received_healing_bonus` | Reserved incoming healing bonus. |
| `pet_efficiency_mult` | Reserved pet efficiency multiplier. |
| `damage_mult` | Global damage multiplier used by some monster size profiles and effects. |
| `thorns_damage_flat` | Reserved reflected/thorns damage. |
| `hand_size` | Feint hand size / tactical hand capacity. |

## Environmental

| Field | Meaning |
| --- | --- |
| `environment_cold_resistance` | Cold/anchor environment resistance; garment implicit profiles can add it. |
| `environment_heat_resistance` | Heat/anchor environment resistance; garment implicit profiles can add it. |
| `environment_gravity_resistance` | Gravity/anchor environment resistance; garment implicit profiles can add it. |
| `environment_bio_resistance` | Biohazard/anchor environment resistance, currently derived from Endurance and garment profiles. |

## World Stats

World stats exist separately from combat modifiers and should not be treated as
combat resolver inputs unless a feature explicitly consumes them.

Current world DTO fields include:

- `trade_discount`
- `sell_price_bonus`
- `social_bonus`
- `crafting_speed`
- `crafting_success_chance`
- `crafting_critical_chance`
- `resource_gathering_bonus`
- `weight_limit_bonus`
- `inventory_slots_bonus`
- `find_loot_chance`
- `skill_gain_bonus`

Item modifier contracts also include some world targets such as `travel_speed`,
`skill_scouting`, `skill_pathfinder`, `resource_find_chance`, and `trade_bonus`.
Those are catalog-ready directions, not proof that every world consumer already
applies them.

## Active Aliases

The character combat math model accepts several old or item-facing names and
maps them to current fields:

| Alias | Current field |
| --- | --- |
| `block_chance` | `block` |
| `damage_reduction_flat` | `armor` |
| `dodge_chance` | `evasion` |
| `energy_max` | `en` |
| `evasion_penalty` | `evasion` |
| `hp_max` | `hp` |
| `magical_resistance` | `magic_resist` |
| `magical_armor` | `magic_armor` |
| `magic_resistance` | `magic_resist` |
| `parry_chance` | `parry` |
| `physical_accuracy` | `accuracy` |
| `physical_crit_chance` | `crit_chance` |
| `physical_crit_power_float` | `crit_power` |
| `shield_block_chance` | `block` |

# Actor Mapper Contract

[Back: Modifiers Reference](./Modifiers_Reference.md)

This file defines how the actor snapshot mapper must fill `raw.modifiers`
before the combat `StatsWaterfallCalculator` builds final `ActorStats`.

The mapper does not calculate final combat values. It only transfers known
layers into:

```json
{
  "base": 0.0,
  "source": {},
  "temp": {}
}
```

## Layer Rules

### `base`

Systemic or intrinsic baseline. Usually comes from attributes or hard system
defaults. It is stored as a plain number.

Examples:

- `hp.base` from `endurance`.
- `evasion.base` from `agility`.
- `physical_damage.base` from `strength`.
- `physical_suppression.base` from `strength`.
- `main_hand_accuracy.base = 0.70` for a weapon hand.
- `main_hand_damage_base.base` from `strength` only for unarmed combat.

### `source`

Stable pre-combat sources. Items, item quality, affixes, permanent gifts,
passives, and skill-derived pre-combat corrections go here.

Values should preserve operation intent. Numeric values are additive by default
only where the modifier contract says so. For the new item/affix system, source
values should be stored as operation strings when the operation is not implicit:

```json
{
  "item:quarterstaff:accuracy_penalty": "-0.08",
  "skill:skill_polearms:accuracy_penalty_refund": "+0.04",
  "affix:duelist:crit_chance": "+0.03",
  "effect:stance:damage_mult": "*1.10",
  "debug:custom": "**2"
}
```

Waterfall must understand the operation prefix, not the mapper.

Supported operation intent:

- `+x`: add.
- `-x`: subtract.
- `*x`: multiply.
- `/x`: divide.
- `**x`: power.
- `=x`: set/fix value.

`=x` is not an additive modifier. It fixes the modifier to a specific value for
the operation duration. It is primarily intended for `temp` entries produced by
skills, effects, abilities, control states, and stances.

Examples:

```json
{
  "effect:blind:accuracy": "*0.50",
  "effect:root:evasion": "=0",
  "ability:true_strike:main_hand_accuracy": "=1"
}
```

Waterfall must give `=` explicit priority rules. Open decision: whether the last
set operation wins, the strongest control wins, or set operations are ordered by
effect priority.

Open decision: whether source values are always strings, or whether plain
numbers remain accepted as additive for backward compatibility.

### `temp`

Runtime combat changes. Buffs, debuffs, control effects, stance changes, and
round-local mutations go here.

`Effect_Schema.md` states that effect `raw_modifiers` are values added into
temp modifiers. Mapper should not pre-apply them.

## Skill Scale

Skills are stored under the hood as normalized floats:

```text
0.0 .. 1.0
```

The UI may display them as percentages:

```text
skill_value * 100
```

Values above `1.0` are valid if items, effects, or systems raise effective
mastery above 100%. Any skill formula must use normalized values and must not
divide by 100 in runtime math.

## Waterfall Responsibility

The mapper emits layers. Waterfall calculates final values.

Correct:

```json
"main_hand_accuracy": {
  "base": 0.70,
  "source": {
    "item:quarterstaff:accuracy_penalty": "-0.08",
    "skill:skill_polearms:accuracy_penalty_refund": "+0.04"
  },
  "temp": {}
}
```

Incorrect:

```json
"main_hand_accuracy": {
  "base": 0.66,
  "source": {},
  "temp": {}
}
```

The second example hides item and skill sources and makes debugging impossible.

## Block 1: Hand Weapon Modifiers

### `main_hand_damage_base`

Meaning: maximum/base weapon damage for main hand.

Mapper contract:

- `base`: strength-derived damage only when unarmed.
- `source`: equipped weapon `power` / base damage.
- `temp`: temporary damage changes from combat effects.

Notes:

- Weapon mastery must not increase maximum/base weapon damage.
- Weapon tier/material/quality may scale weapon power before it becomes source.
- Inventory comparison should compare generated item power before waterfall,
  and final combat output after waterfall.

Current design status: defined.

### `off_hand_damage_base`

Meaning: maximum/base weapon damage for off hand.

Mapper contract:

- `base`: normally `0`.
- `source`: off-hand weapon power.
- `temp`: temporary combat effects.

Skill interaction:

- `skill_dual_wield` does not change weapon base itself.
- It changes effective off-hand damage quality, likely as a source multiplier
  or runtime rule.

Current design status: defined, exact dual-wield operation still needs final
formula.

### `main_hand_damage_spread`

Meaning: damage variance around weapon damage.

Mapper contract:

- `base`: system default only if no weapon-specific spread exists.
- `source`: weapon `damage_spread`.
- `temp`: temporary spread changes.

Skill interaction:

- Weapon mastery compresses spread and shifts the practical damage range toward
  the high end.
- This should not raise maximum/base weapon damage.
- Exact implementation may be a waterfall source operation or a runtime damage
  roll rule.

Current design status: concept defined, exact operation pending.

### `off_hand_damage_spread`

Same as main hand, but off-hand. Dual wield may also affect stability.

Current design status: concept defined, exact operation pending.

### `main_hand_accuracy`

Meaning: main-hand hit chance before global accuracy bonuses and target defense.

Mapper contract:

- `base`: weapon-hand system base, expected `0.70`.
- `source`: weapon `accuracy_penalty` as negative operation string.
- `source`: weapon mastery refund as positive operation string.
- `temp`: blind, stance, control, temporary combat effects.

Example:

```json
"main_hand_accuracy": {
  "base": 0.70,
  "source": {
    "item:quarterstaff:accuracy_penalty": "-0.08",
    "skill:skill_polearms:accuracy_penalty_refund": "+0.08"
  },
  "temp": {}
}
```

At skill `1.0`, mastery should fully neutralize the item penalty. At skill
above `1.0`, the refund may exceed the item penalty and become a real accuracy
bonus.

Current design status: defined.

### `off_hand_accuracy`

Meaning: off-hand hit chance.

Mapper contract:

- `base`: weapon-hand system base, expected `0.70` when an off-hand weapon is equipped.
- `source`: off-hand weapon `accuracy_penalty` as negative operation string.
- `source`: `skill_dual_wield` refund for off-hand penalty.
- `temp`: runtime effects.

Current design status: defined, exact dual-wield refund formula pending.

### `main_hand_crit_chance`

Meaning: chance to trigger weapon crit/item trigger from main hand.

Mapper contract:

- `base`: normally `0`.
- `source`: weapon base trigger chance.
- `source`: quality/tier/material scaling of trigger chance.
- `source`: weapon mastery trigger chance contribution.
- `temp`: temporary crit/trigger effects.

Notes:

- In this combat model, crit is the activation of an item trigger.
- Weapon tier may scale trigger chance.
- Weapon mastery improves trigger chance/effectiveness, not maximum weapon damage.

Current design status: defined conceptually, exact tier/skill formula pending.

### `off_hand_crit_chance`

Same as main hand, but off-hand. Dual wield may affect off-hand trigger quality.

Current design status: concept defined, exact formula pending.

## Block 2: Global Physical Modifiers

### `physical_damage`

Meaning: attribute-derived physical damage baseline. Strength provides this value
for unarmed attacks and as the global physical bonus available to weapon attacks.

Mapper contract:

- `base`: strength-derived physical damage from `Attributes/README.md`.
- `source`: possible gifts/passives/items.
- `temp`: buffs/debuffs.

Current design status: defined by the Attributes design. Runtime must not replace
this with Agility/Perception-era legacy formulas.

### `physical_damage_bonus`

Meaning: global physical damage bonus for physical attacks.

Mapper contract:

- `base`: normally `0`.
- `source`: item affixes, gifts, passives.
- `temp`: buffs/debuffs/stances.

Current design status: defined.

### `accuracy`

Meaning: global accuracy bonus added to hand/magic accuracy by resolver.

Mapper contract:

- `base`: normally `0`.
- `source`: item affixes, buffs, gifts.
- `temp`: blind/accuracy buff/debuff.

Notes:

- This is not weapon base accuracy.
- Base weapon hand accuracy belongs to `main_hand_accuracy` or `off_hand_accuracy`.

Current design status: defined.

### `physical_suppression`

Meaning: natural physical suppression that reduces `physical_resistance`.
It is not armor penetration and does not reduce flat `armor`.

Mapper contract:

- `base`: strength-derived physical suppression, `strength * 0.02`.
- `source`: item affixes, feints, passives.
- `temp`: buffs/debuffs.

Current design status: defined by the Attributes design.

### `armor_penetration_pct`, `armor_penetration_flat`, `armor_ignore_chance`

Meaning: armor-layer penetration against flat `armor`.

Mapper contract:

- `base`: normally `0`.
- `source`: weapon properties, item affixes, passives.
- `temp`: buffs/debuffs and feints.

Current design status: defined by combat resolver.

### `crit_chance`

Meaning: global crit/trigger chance bonus added to hand crit chance.

Mapper contract:

- `base`: normally `0`.
- `source`: item affixes, gifts, passives.
- `temp`: buffs/debuffs.

Current design status: defined.

### `crit_power`

Meaning: critical effect power if used by triggers/damage.

Mapper contract:

- `base`: normally `0` or system default if crit power becomes a multiplier.
- `source`: item affixes, gifts, trigger definitions.
- `temp`: buffs/debuffs.

Current design status: unclear. Needs trigger contract.

## Block 3: Active Defense

### `evasion`

Meaning: dodge/evasion chance before caps and anti-dodge.

Mapper contract:

- `base`: agility-derived evasion, `agility * 0.05`.
- `source`: item affixes and item penalties.
- `source`: two-handed/shield/heavy gear evasion penalties.
- `source`: tactical skill refunds for style penalties.
- `temp`: blind, root, control, combat buffs/debuffs.

Current design status: defined conceptually, exact style penalty/refund formula pending.

### `dodge_cap`

Meaning: hard cap for evasion.

Mapper contract:

- `base`: system default, currently DTO default `0.75`.
- `source`: rare item/gift cap modifiers.
- `temp`: temporary cap changes if effects support them.

Current design status: defined.

### `anti_dodge_chance`

Meaning: hit tracing / reduction of target evasion.

Mapper contract:

- `base`: perception-derived anti-evasion, `perception * 0.03`.
- `source`: items, affixes, buffs.
- `temp`: combat effects.

Current design status: defined.

### `parry`

Meaning: chance to parry.

Mapper contract:

- `base`: normally `0`; attributes do not grant passive parry.
- `source`: weapon or off-hand parry property.
- `temp`: combat effects.

Current design status: base chance is supplied by equipment. `skill_parrying`
multiplies this chance inside `CombatResolver`, not in the mapper/waterfall.

### `parry_cap`

Meaning: hard cap for parry.

Mapper contract:

- `base`: system default, currently DTO default `0.50`.
- `source`: rare item/gift cap modifiers.
- `temp`: temporary cap changes.

Current design status: defined.

### `block`

Meaning: shield block chance.

Mapper contract:

- `base`: normally `0`.
- `source`: shield `shield_block_chance`.
- `temp`: combat effects.

Current design status: block is chance only. Shield/off-hand power belongs to
`armor`, not `block`. `skill_shield_mastery` is a separate shield mechanic and
does not directly raise block chance; current resolver uses `skill_parrying` as
the active defense multiplier for shield block.

### `shield_block_cap`

Meaning: hard cap for shield block.

Mapper contract:

- `base`: system default, currently DTO default `0.75`.
- `source`: rare item/gift cap modifiers.
- `temp`: temporary cap changes.

Current design status: defined.

## Block 4: Mitigation And Resistances

### `armor`

Meaning: flat physical damage reduction from armor.

Mapper contract:

- `base`: normally `0`.
- `source`: armor item power.
- `source`: armor quality/tier/material scaling.
- `temp`: temporary armor buffs/debuffs.

Current design status: defined.

### `physical_resistance`

Meaning: percent physical resistance.

Mapper contract:

- `base`: endurance-derived resistance, `endurance * 0.02`.
- `source`: item affixes, gifts, passives.
- `temp`: buffs/debuffs.

Current design status: defined.

### `magic_resist`

Meaning: percent magical resistance.

Mapper contract:

- `base`: mental-derived resistance, `mental * 0.02`.
- `source`: item affixes, gifts, passives.
- `temp`: buffs/debuffs.

Current design status: defined.

### `resistance_cap`

Meaning: hard cap for resistances.

Mapper contract:

- `base`: system default, currently DTO default `0.85`.
- `source`: rare item/gift cap modifiers.
- `temp`: temporary cap changes.

Current design status: defined.

## Block 5: Magical And Item Attack Modifiers

### `magical_damage`

Mapper contract:

- `base`: intellect-derived magical damage.
- `source`: spell focus/wand/staff if applicable.
- `temp`: buffs/debuffs.

Current design status: defined by the Attributes design; DTO uses
`magical_damage`.

### `magical_damage_spread`

Mapper contract:

- `base`: system/default magical spread.
- `source`: wand/staff/spell source.
- `source`: spell mastery stability if implemented.
- `temp`: effects.

Current design status: partly defined.

### `magical_accuracy`

Mapper contract:

- `base`: system/default magic accuracy if any.
- `source`: wand/spell/item source.
- `temp`: effects.

Current design status: partly defined.

### `item_damage_base`, `item_damage_spread`, `item_accuracy`, `item_crit_chance`, `item_armor_penetration_pct`

Meaning: combat items such as grenades, scrolls, throwable items.

Mapper contract:

- `base`: normally `0`.
- `source`: item definition and item quality/tier.
- `temp`: effects.

Current design status: not reviewed. Needs item-use contract.

## Block 6: Status, Special, Environment, Speed

These modifiers are not fully reviewed in the actor mapper pass yet.

Known broad rules:

- Attribute-derived resistances go into `base`.
- Item, affix, gift, passive values go into `source`.
- Combat effects go into `temp`.
- Caps are system `base` unless specifically modified by item/gift/effect.

Needs per-modifier review:

- elemental damage/resistance fields.
- control/status fields.
- vampiric fields.
- healing fields.
- pet fields.
- thorns.
- hand size.
- environment resistance.
- attack/cast/movement speed.

## Affix Contract

Affixes must be reworked for operation-aware waterfall input.

Current problem:

- If a modifier starts at `0`, multiplicative affixes like `*1.10` do nothing
  unless there is a meaningful base/source value before multiplication.
- Additive affixes are safe with zero, but multiplicative/divisive/power affixes
  require explicit operation and ordering.

Required affix fields:

```json
{
  "target_field": "main_hand_crit_chance",
  "operation": "+",
  "base_value": 0.03
}
```

Alternative compact source value:

```json
{
  "target_field": "main_hand_crit_chance",
  "value": "+0.03"
}
```

Open decision: use explicit structured fields for authoring and convert to
operation strings in mapper, or store operation strings directly in resources.

## Inventory Comparison

Inventory UI should compare both:

- generated item mechanics before waterfall: power, spread, penalty, trigger chance, affixes;
- final actor stats after waterfall: effective damage range, effective accuracy,
  crit/trigger chance, defense totals.

Do not hide source layers by collapsing them into base before comparison.

## Open Implementation Questions

1. Should mapper always emit operation strings in `source/temp`, while `base`
   remains numeric?
2. Should plain numeric `source` remain additive for backward compatibility?
3. Where exactly does skill refund live: mapper-emitted `source`, or waterfall
   formula that reads skill and item penalty metadata?
4. Do we need separate fields for trigger chance vs crit chance, or does
   `*_crit_chance` remain trigger activation chance?
5. Should weapon `damage_spread` compression be expressed as waterfall operation
   or handled in damage roll runtime?
6. Should the Strength damage coefficient stay at the current 1.0 per point, or
   become a tunable 1-2 range as described in the Attributes design?

# Actor Mapper Reference

Status: current technical reference with pending design notes.

The actor mapper builds raw math input for the combat stats waterfall. It should
preserve source layers and avoid hiding item, skill, effect, and attribute
contributions inside pre-computed final values.

## Runtime Shape

Actor raw math is stored under:

```json
{
  "attributes": {},
  "modifiers": {},
  "rules": {},
  "pipeline": {}
}
```

Each raw attribute or modifier uses:

```json
{
  "base": 0.0,
  "source": {},
  "temp": {}
}
```

## Layer Rules

### `base`

`base` is the intrinsic value supplied by the actor model or item model before
temporary runtime changes.

Current examples:

- primary attributes use `base` for the actor's attribute values;
- unarmed actors write Strength into `main_hand_damage_base.base`;
- equipped weapon power is written into hand damage base;
- armor power is written into `armor.base`;
- item damage spread may replace the relevant spread base.

Do not write the resolver's built-in `0.60` hit baseline into
`main_hand_accuracy.base` or `off_hand_accuracy.base`. The hit baseline is
resolver-owned.

### `source`

`source` contains stable pre-combat contributions.

Examples:

- item affixes;
- item implicit bonuses that are projected as commands;
- permanent Gifts or passives, once implemented;
- monster family or size profile modifiers;
- skill-derived source corrections, if a future rule emits them before combat.

`source` values can be plain numbers or operation commands. Operation commands
are supported by the waterfall and used by compiled modifier contracts, but the
current code still allows plain numeric additive values.

Supported operation command forms:

- `+x`
- `-x`
- `*x`
- `/x`
- `=x`

The `=x` command resets the current expression to a fixed value in the current
waterfall evaluation. Use carefully for control states or explicit set effects.

### `temp`

`temp` contains runtime combat changes:

- buffs;
- debuffs;
- control effects;
- stance effects;
- active ability effects;
- other reversible temporary state.

Effect and ability services should write temp entries with rollback metadata.
The resolver must read rebuilt `ActorStats`, not raw temp data directly.

## Waterfall Responsibility

The mapper emits raw layered values. `StatsWaterfallCalculator` calculates final
flat values.

The flow is:

1. calculate final primary attributes;
2. derive modifier commands from the selected attribute profile;
3. combine derived values with modifier base/source/temp;
4. assemble weapon base power from weapon power, weighted stat power, and weapon
   mastery;
5. produce flat `ActorStats.mods`.

Resolver input is `ActorStats`, not `ActorSnapshot.raw`.

## Attribute Bridge

Attribute-derived combat values are owned by the attribute bridge rules. The
bridge applies the effective-attribute curve before coefficients:

```text
effective(stat) = stat * stat / 11
```

Examples:

- Strength derives `physical_strength_power` and `physical_suppression`;
- Agility derives `physical_agility_power`, `evasion`, and `initiative`;
- Endurance derives `physical_endurance_power`, health, physical resistance,
  poison resistance, bleed resistance, and bio environment resistance;
- Intellect derives `magical_damage` and `magical_penetration`;
- Mental derives magic/control/mental/elemental resistances;
- Perception derives `anti_dodge_chance`;
- Memory and Prediction derive `counter_attack_chance`.

`physical_endurance_power` is available to style-specific mechanics such as
shield guard scaling, but ordinary weapon damage uses effective Strength and
Agility only.

See `docs/game-design/rules/attributes/technical_reference.md` for the current
formula table and monster profile differences.

## Character Mapper

Current character raw math is built by:

```text
src/backend/features/character/runtime/combat_math_model.py
```

Responsibilities:

- copy active character attributes into raw attributes;
- map equipped item mechanics into raw modifiers;
- apply item power to hand damage, armor, or shield guard fields;
- apply item implicit bonuses and affixes;
- apply armor dodge-cap rules;
- apply unarmed fallback when no main-hand weapon exists;
- preserve aliases for legacy/item-facing modifier names.

## Monster Mapper

Current monster raw math is built by:

```text
src/backend/features/monsters/runtime/combat_math_model.py
```

The monster builder starts from the character math builder, then applies:

- monster tags;
- `rules.attribute_profile = monster:<archetype>`;
- monster pipeline metadata;
- size modifiers.

Current monster size modifiers:

| Size | Source modifiers |
| --- | --- |
| `small` | `evasion +0.05`, `physical_resistance -0.02`, `damage_mult *0.9` |
| `medium` | no extra size modifiers |
| `large` | `hp +20`, `evasion -0.03`, `physical_resistance +0.03`, `damage_mult *1.1` |
| `huge` | `hp +50`, `evasion -0.06`, `physical_resistance +0.06`, `damage_mult *1.25` |

Monster attribute profile rules are documented in the attributes technical
reference.

## Skill Scale

Combat skills are normalized floats:

```text
0.0 .. 1.0
```

Values above `1.0` can exist through effects or items. Runtime math should not
divide skill values by 100.

UI may display skills as `skill_value * 100`.

## Resolver-Owned Math

The mapper must not duplicate resolver formulas.

Examples of resolver-owned behavior:

- hit baseline and skill hit bonus;
- evasion check against `anti_dodge_chance` and `dodge_cap`;
- parry and shield block skill multipliers;
- counter-attack check;
- crit / trigger chance cap;
- physical resistance and armor mitigation;
- branch selection for main hand, off hand, magic, or item actions.

Weapon base-power assembly is owned by `StatsEngine` after the waterfall, not by
the mapper and not by the resolver. The mapper keeps weapon power in
`{hand}_damage_base`; the assembler stores that original value in
`{hand}_weapon_power`, adds mastered stat damage into `{hand}_damage_base`, and
keeps trace fields for UI/tooltips.

## Modifier Aliases

The mapper accepts old or item-facing aliases and normalizes them before writing
to raw modifiers.

See `modifier_vocabulary.md` for the alias table.

## Item Affix Contract

Item affixes compile through modifier contracts.

Current contract root:

```text
src/backend/features/items/resources/modifier_contracts/
```

Contracts define:

- target field;
- operation;
- value kind;
- default layer;
- tags.

If the contract target is an attribute, the mapper writes into raw attributes.
If the target is a combat modifier, it writes into raw modifiers. If the target
is world-only and not a combat modifier, combat projection filters it out.

## Pending Areas

These areas exist as fields or design directions but need feature-specific
implementation before being treated as complete gameplay behavior:

- combat item action fields;
- vampiric modifiers;
- healing modifiers beyond current resolver behavior;
- pet modifiers;
- elemental damage bonuses;
- full world modifier consumers;
- sockets/gems/inserts;
- Gift-derived source modifiers.

## Common Mistakes

- Do not write old names like `hp_max`, `energy_max`, `dodge_chance`, or
  `magical_damage_base` into new docs as canonical field names.
- Do not write resolver hit baseline into hand accuracy base.
- Do not collapse item or affix contributions into a hidden final number when a
  source label can be preserved.
- Do not make a design doc the field-level schema source. Code DTOs and tests
  own runtime fields.
- Do not add a new modifier just because it appears in an old design note; first
  verify the DTO, mapper, modifier contract, and resolver/world consumer.

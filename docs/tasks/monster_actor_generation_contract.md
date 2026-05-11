# Monster Actor Generation Contract

This document freezes the first three contracts for generated monster actors:

1. generated monster database template;
2. target family resource structure;
3. typed JSON field DTOs used to validate generated monster payloads.

It describes the target data shape before database migrations, item generation,
or runtime rewrites.

## Scope

The generated monster database row is an active monster template inside a generated
clan. It is not the full family resource and it is not a live combat session state.

The generated monster row must contain enough data for a later combat actor builder
to produce the same combat snapshot shape used by player actors:

```python
{
    "meta": ...,
    "source": ...,
    "status": vitals,
    "combat": {
        "math_model": raw_attributes_and_modifiers,
        "skills": flat_skills,
        "loadout": {
            "layout": combat_layout,
            "equipment_layout": item_ids,
            "belt": quick_items,
            "known_abilities": ...,
            "known_feints": ...,
        },
    },
}
```

The generated monster row should store actor-builder inputs, not prebuilt combat
`math_model` output.

## Boundary

### Family Resource

Family resources describe what a family can generate:

- family key, archetype, organization type;
- composition rules and cost scaling;
- available variant keys;
- variant tier availability;
- attribute budgets or base attributes;
- skill kit: base, role bonus, variant overrides;
- available monster equipment mappings;
- allowed affix pools;
- allowed granted abilities when ability content exists;
- text and AI generation hints;
- loot and salvage rules.

Family resources are not copied wholesale into each generated monster row.

### Generated Clan Row

The clan row remains the shared container for generated members:

- `id`
- `family_id`
- `tier`
- `zone_id`
- `context_hash`
- `unique_hash`
- `raw_tags`
- clan-level text/flavor content

The clan tier is the context tier used to create the clan. Monster rows do not need
to duplicate that value unless a future query needs direct filtering without joining
the clan.

### Generated Monster Row

The monster row stores what was actually granted to one generated member:

- identity within the generated clan;
- role and member tier;
- text for encounter presentation;
- actor metadata/tags;
- scaled attributes;
- scaled combat skills;
- generated runtime item projection;
- granted abilities;
- AI profile;
- balance/cost data.

It does not store live combat state.

## Target Columns

Recommended target columns for `generated_monsters`:

```text
id UUID primary key
clan_id UUID foreign key
schema_version int

variant_key string
role string
member_tier int

text_content JSONB
meta JSONB

scaled_attributes JSONB
scaled_skills JSONB
items JSONB
granted_abilities JSONB
ai_profile JSONB
balance JSONB
```

Legacy field mapping:

```text
scaled_base_stats -> scaled_attributes
loadout_ids       -> items.layout.equipment, then generated items.by_id
skills_snapshot   -> granted_abilities or legacy action keys
threat_rating     -> balance.threat_rating
combat_seed       -> remove from persistent source-of-truth
current_state     -> remove from generated template source-of-truth
```

Current code status:

- legacy runtime DTO: `GeneratedMonster`;
- target row contract DTO: `GeneratedMonsterTemplateDTO`;
- no ORM migration yet.

## Field Semantics

### `schema_version`

Version of the generated monster row shape.

### `variant_key`

The resource variant key such as `sewer_rat`.
This is not a global database template id.

### `role`

Combat/encounter role:

```text
minion | veteran | elite | boss
```

### `member_tier`

The tier used to scale this generated member's attributes, skills, and generated
items.

The parent clan stores the context tier. A role policy can derive member tier from
the clan tier, for example:

```text
minion  -> clan_tier - 1
veteran -> clan_tier
elite   -> clan_tier
boss    -> clan_tier + 1
```

The final value must be clamped to the supported tier range.

### `text_content`

Text content for encounter presentation. This should be a single JSON object, not
separate top-level name/description columns.

Expected shape:

```json
{
  "name_ru": "Sewer Rat",
  "short_name_ru": "rat",
  "appearance_ru": "...",
  "detected_ru": "...",
  "ambush_ru": "...",
  "idle_ru": "..."
}
```

### `meta`

Stable actor metadata and tags that are not combat formulas:

```json
{
  "archetype": "beast",
  "tags": ["monster", "beast", "rat", "swarm", "minion"]
}
```

### `scaled_attributes`

Final generated attributes for the member. Use the same attribute keys used by
player combat actors:

```json
{
  "strength": 4,
  "agility": 12,
  "endurance": 6,
  "intellect": 1,
  "memory": 1,
  "mental": 2,
  "perception": 7,
  "projection": 1,
  "prediction": 2
}
```

These are inputs to the later combat math model builder.

### `scaled_skills`

Final generated combat skills for the member. Skill ids must be the same catalog
skill ids used by players. Do not introduce monster-only skill ids unless they are
also real catalog skills.

Example:

```json
{
  "skill_daggers": 0.20,
  "skill_light_armor": 0.05
}
```

Family `skill_kit` remains a good source shape:

```text
base + role_bonus + variant_overrides -> scaled_skills
```

### `items`

Runtime item projection for the monster, shaped like player `items` input:

```json
{
  "layout": {
    "equipment": {
      "main_hand": "monster_item:<monster_id>:main_hand",
      "off_hand": "monster_item:<monster_id>:off_hand",
      "chest_armor": "monster_item:<monster_id>:chest_armor"
    },
    "belt": {}
  },
  "by_id": {
    "monster_item:<monster_id>:main_hand": {
      "item_id": "monster_item:<monster_id>:main_hand",
      "base_id": "dagger",
      "item_type": "weapon",
      "slot": "main_hand",
      "placement": "equipped",
      "name": "Rat Claws",
      "description": "Monster natural weapon.",
      "rarity": "shared",
      "rarity_tier": 1,
      "mechanics": {},
      "tags": ["monster", "natural_weapon", "rat"],
      "metadata": {
        "family_id": "rat_swarm",
        "monster_equipment_key": "rat_claws",
        "source_base_id": "dagger"
      }
    }
  }
}
```

Important rules:

- `layout.equipment` points to item ids inside `by_id`, as with player actors.
- `by_id` contains generated runtime item projections, not only base ids.
- These generated items are derived from normal item bases plus monster tier
  scaling and allowed family affixes.
- They should not go through unique naming/loot generation unless explicitly
  required later.

### `granted_abilities`

Abilities actually granted to this generated monster.

If the ability system is not ready for monsters, this can be empty:

```json
{
  "known_abilities": []
}
```

Basic attacks should come from item/loadout/feint flow where possible, not from a
fake ability entry.

### `ai_profile`

Compact behavior data for the AI worker:

```json
{
  "behavior": "swarm_chaff",
  "targeting": "nearest_or_weakest",
  "range": "melee",
  "group_logic": "overwhelm"
}
```

This is not an LLM prompt. It is structured runtime guidance.

### `balance`

Generated cost data for encounter assembly:

```json
{
  "base_cost": 20,
  "effective_cost": 4,
  "threat_rating": 20,
  "organization_type": "swarm",
  "organization_divisor": 5.0
}
```

Encounter assembly should use `effective_cost` when spending encounter budget,
while `threat_rating` can remain a public/debug measure of rank pressure.

## Family Resource Target Structure

The target family resource needs a clan model plus member models. This keeps
source-family design separate from generated monster database rows.

Target top-level shape:

```text
family
- id
- archetype
- organization_type
- default_tags
- hierarchy                    # legacy validation and role buckets
- clan_model                   # new target contract
- member_models[]              # new target contract
- variants                     # legacy variants until migration
```

`clan_model` describes what the family can generate:

```text
clan_model
- tier_range
- balance
- text_hints
- ai_defaults
- item_mappings
- allowed_affix_pools
```

`member_models[]` describes generation rules for each member variant:

```text
member_model
- variant_key
- role
- tier_policy
- member_tier_offset
- attribute_profile
- skill_profile
- item_loadout_profile
- ability_profile
- ai_profile
- balance
```

Current code status:

- target DTOs: `MonsterClanResourceModelDTO` and
  `MonsterMemberResourceModelDTO`;
- typed resource helper structs: `MonsterClanResourceModel` and
  `MonsterMemberResourceModel`;
- existing families are not migrated yet.

The old `hierarchy` field can still validate role buckets, but it must not be
treated as the runtime composition algorithm.

## JSON Field DTOs

The generated monster JSONB fields have typed contracts:

```text
text_content       -> MonsterTextContentDTO
meta               -> MonsterMetaDTO
scaled_attributes  -> MonsterScaledAttributesDTO
scaled_skills      -> MonsterScaledSkillsDTO
items              -> MonsterItemsProjectionDTO
granted_abilities  -> MonsterGrantedAbilitiesDTO
ai_profile         -> MonsterAIProfileDTO
balance            -> MonsterBalanceDTO
```

Validation rules already fixed in code:

- `scaled_attributes` uses player-compatible attribute keys:
  `strength`, `agility`, `endurance`, `intellect`, `memory`, `mental`,
  `perception`, `projection`, `prediction`;
- `scaled_skills.skills` must use player catalog-style ids with `skill_`;
- `items.layout.equipment` and `items.layout.belt` must reference item ids that
  exist in `items.by_id`.

## Builder Order

There are two different builders and they must not be confused.

### Generation Builder

This runs first. It creates clans and generated monster database rows from:

- biome and context;
- clan/family resource;
- variant availability;
- role/member tier policy;
- skill kit;
- item mappings;
- allowed affixes;
- AI/text rules.

This is the builder that writes `generated_clans` and `generated_monsters`.

### Combat Actor Builder

This runs later. It reads a generated monster row and produces the combat actor
snapshot. It should be implemented after the generated monster row has the new
contract shape.

The combat actor builder must derive:

- `status` from `scaled_attributes`;
- `combat.math_model` from `scaled_attributes`, `scaled_skills`, and `items`;
- `combat.skills` from `scaled_skills`;
- `combat.loadout` from `items`, `granted_abilities`, and known feint rules.

## Non-Goals For Stage 1

- No database migration.
- No runtime behavior change.
- No family archive move.
- No encounter assembly rebalance.
- No combat actor builder implementation.
- No generated item builder implementation.

## Stop Before Stage 4

The next stage is item mapping/generation discussion. No implementation in this
document decides how `rat_bite_claws` becomes a generated item projection from a
base item, tier scaling, and affix pool.

---
name: turnbasedmmorpg-monster-family
description: Monster family resource guidance for TurnBasedMMORPG. Use when creating, editing, registering, validating, or reviewing monster families, variants, roles, variant skill lists, monster item inputs, narrow monster loadouts, loot profiles, generated monster templates, or monster actor snapshot compatibility.
---

# TurnBasedMMORPG Monster Family

## First Reads

Read these before changing monster family resources:

- `docs/agent-skills/turnbasedmmorpg-project/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-backend/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-skill-catalog/SKILL.md`
- `src/backend/features/monsters/dto/resources.py`
- `src/backend/features/monsters/resources/__init__.py`
- `src/backend/features/monsters/resources/monster_structs.py`
- `src/backend/features/monsters/resources/families`
- `src/backend/features/monsters/runtime/clan_factory.py`
- `src/backend/features/monsters/runtime/generation_fields.py`
- `src/backend/features/monsters/runtime/combat_actor_input.py`
- `src/backend/features/monsters/skill_contract.py`
- `src/backend/features/items/resources/bases.py`
- `tests/backend/features/monsters/runtime/test_generation_fields.py`
- `tests/backend/features/monsters/runtime/test_combat_actor_input.py`

When editing numeric monster skills, also inspect the catalog definitions under `src/backend/features/game_catalog/skills`.

## Ownership

- Family resources live in `src/backend/features/monsters/resources/families/*.py`.
- The active registry is owned by `src/backend/features/monsters/resources/__init__.py`.
- Only families imported into `ALL_FAMILIES_RAW` are runtime-loaded. Many dormant family modules are DTO-valid but unavailable to spawning/combat until registered.
- Spawn biome/tier availability lives in `src/backend/features/monsters/resources/spawn_config.py`, but spawn config does not register a family by itself.
- Monster item inputs flow through the item-generation/runtime item projection path. Do not model monsters as full player paperdolls.

## Family Shape

Use `MonsterFamilyDTO` as the active contract. `monster_structs.py` is a typing aid and contains some legacy fields that DTO/runtime ignore.

Required top-level fields:

- `id`: stable lowercase snake case family id.
- `archetype`: one of `humanoid`, `beast`, `undead`, `construct`, `demon`, `unknown`.
- `organization_type`: one of `solitary`, `pack`, `gang`, `clan`, `legion`, `horde`, `swarm`.
- `hierarchy`: role buckets that reference variant ids.
- `variants`: mapping of variant key to variant object.

Effectively required for combat-ready families:

- `loot_profile`
- each combat-ready variant has an explicit `skills` list

Defaulted or optional fields:

- Top level: `default_tags`, `loot_profile`, `clan_model`, `member_models`.
- Variant: `extra_tags`, `min_tier`, `max_tier`, `fixed_loadout`, `skills`, `member_model`.

Do not add old/future-hook fields such as `ability_map`, `combat_profile`, `ability_overrides`, `body_loadout`, `equipment_scaling`, or `modifier_formula` unless the runtime DTOs and consumers are implemented in the same task.

## Variants And Roles

Roles are only:

- `minion`
- `veteran`
- `elite`
- `boss`

Each variant must define:

- `id`
- `role`
- `narrative_hint`
- `cost`
- `base_stats`

Rules:

- `hierarchy` entries must reference existing variant ids. DTO validation enforces this.
- Keep the variant dict key equal to `variant.id`; current DTO validation does not enforce this, but registry and generated monster code assume stable ids.
- Use `min_tier` and `max_tier` to gate variant availability. `get_available_variants_for_tier_window()` may include neighbor-tier variants around the current tier.
- `base_stats` must include `strength`, `agility`, `endurance`, `intellect`, `memory`, `mental`, `perception`, `projection`, and `prediction`.
- Put combat skill availability in `variant.skills`; do not store skill percentages in resources.

## Skills

Skills are numeric, trainable game skills. They are not abilities.

Monster resources store skill availability, not skill percentages.

- `variant.skills` is the explicit skill set for that monster variant.
- `member_model.skill_profile.base` may add skill keys for generated member models.
- Generated skill values are computed centrally from `member_tier / 7`, capped at `1.0`.
- Current generated monster skills are filtered through `filter_monster_combat_skills()` and only actor-snapshot combat skill keys are kept.

Use only real catalog ids such as `skill_unarmed`, `skill_archery`, or `skill_light_armor`; do not use ability ids, aggregate keys such as `survival`, or invented monster ability names in skill maps.

## Equipment And Loadouts

Monster combat loadouts are intentionally narrow. Do not expand monsters into a full humanoid paperdoll.

Allowed combat-facing equipment slots for current monster design:

- `main_hand`
- `off_hand`
- `body`

Do not add or normalize toward `head_armor`, `arms_armor`, `legs_armor`, `feetwear`, rings, amulet, belt, or other full gear slots. The project intentionally concentrates item power into fewer item slots with larger affix capacity instead of spreading power across a full equipment doll.

`body` is equipment, not an abstract defensive layer or a path toward full paperdoll gear. It maps to a base item exactly like the hand slots, and item generation later enriches that base item with material, quality, affixes, triggers, and source context.

Humanoids and other item-using monsters may provide base item/loadout intent for `main_hand`, `off_hand`, and `body`. Monster families should not hand-author final generated item stats when the item generator owns that enrichment.

Every referenced item id must resolve through item resources/generation. Validate references when editing families.

Humanoid/item-using families should use item/equipment drop profiles. Beast and non-equipment monsters should use ingredient/material/salvage profiles.

## Abilities And Loot

Monster abilities are currently empty in the active generation path.

- Do not add `ability_map`.
- Do not mix abilities into `variant.skills`.
- `build_granted_abilities()` currently returns an empty `MonsterGrantedAbilitiesDTO`.

`loot_profile` is declarative today. Tests and game catalog projections read it, but no active loot resolver was found. Current conventions:

- Humanoid/item-using families drop generated equipment/items.
- Beast and non-equipment monster families drop ingredients, materials, or salvage.
- Do not use `allowed_loadout_slots="full_humanoid"` as a reason to add full humanoid equipment slots to the monster combat model.

## Combat Snapshot Compatibility

Generation turns family resources into generated monster template fields:

- `variant_key` from `variant.id`
- `role` from `variant.role`
- `member_tier`
- `text_content`
- `meta`
- `scaled_attributes`
- `scaled_skills`
- `items`
- `granted_abilities` (currently empty)
- `ai_profile`
- `balance`

Monster actor snapshots are built by `MonsterCombatActorInputBuilder` from generated monster rows. Keep compatibility in mind when changing family resources: persisted generated monsters may carry old `scaled_skills`, item projections, text, meta, and balance data until regenerated.

## Naming Rules

- Use lowercase snake case for family ids, variant ids, ability ids, and item ids.
- Use catalog skill ids with the `skill_` prefix for numeric skills.
- Do not put geography in `default_tags`; biome/tier selection belongs in `spawn_config.py`.
- Keep skills and abilities distinct. `skill_unarmed` is a numeric trainable skill; an ability such as `bite` or `howl` would be a separate usable action, but monster abilities are not currently populated.

## Common Mistakes

- Adding a family module but not importing it into `ALL_FAMILIES_RAW`.
- Adding a family to `spawn_config.py` without registering it.
- Adding `ability_map` or `combat_profile` because an old design note mentions them.
- Mixing abilities into `variant.skills`.
- Expanding monster loadouts into full humanoid gear slots.
- Treating humanoids as full paperdoll actors instead of item-using monsters with narrow combat slots and generated item drops.
- Referencing item ids that are not registered as item bases.
- Copying ignored fields from `monster_structs.py` such as `name_ru`, `description`, `combat_intro_text`, `_family_ref`, or `_archetype`.
- Assuming `loot_profile` currently performs runtime loot drops.
- Mixing `0..100` skill values and normalized `0.0..1.0` values without checking the active runtime boundary.

## Known Docs/Code Disagreements

- `docs/game-design/rpg-rules/Monsters` does not exist in the current workspace.
- Older notes mention `ability_map`, `combat_profile`, `skills_snapshot`, and monster combat seeds, but the current DTO/generation path does not use those fields.
- Skill design docs may describe `0..100`, while current generated monster runtime expects normalized floats.
- `monster_structs.py` includes fields ignored by DTO/runtime, including presentation and service fields.
- Dormant family files validate but are not loaded by the current starter registry.
- `spawn_config.py` references dormant family ids that cannot spawn until those families are registered.

## Verification

Run focused monster runtime checks after family changes:

```powershell
.\.venv\Scripts\pytest.exe tests\backend\features\monsters\runtime\test_generation_fields.py tests\backend\features\monsters\runtime\test_combat_actor_input.py --no-cov
```

Useful read-only registry check:

```powershell
.\.venv\Scripts\python.exe -c "from src.backend.features.monsters.resources import get_all_family_configs; print(sorted(get_all_family_configs()))"
```

When changing item ids or skill ids, also run focused item/catalog checks and search references:

```powershell
rg -n "skill_[a-z_]+|<item_id>|<family_id>|<variant_id>" src tests docs
```

---
name: turnbasedmmorpg-monster-family
description: Monster family resource guidance for TurnBasedMMORPG. Use when creating, editing, registering, validating, or reviewing monster families, variants, roles, skill_kit values, monster abilities, loot profiles, natural weapons/armor, monster loadouts, combat_profile data, generated monster combat seeds, or monster actor snapshot compatibility.
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
- `src/backend/features/monsters/runtime/combat_profile.py`
- `src/backend/features/items/resources/bases.py`
- `src/backend/features/items/resources/monster_equipment/natural.py`
- `tests/backend/features/monsters/runtime/test_registry_and_combat_profile.py`
- `tests/backend/features/monsters/runtime/test_clan_factory.py`

When editing numeric monster skills, also inspect the catalog definitions under `src/backend/features/game_catalog/skills`.

## Ownership

- Family resources live in `src/backend/features/monsters/resources/families/*.py`.
- The active registry is owned by `src/backend/features/monsters/resources/__init__.py`.
- Only families imported into `ALL_FAMILIES_RAW` are runtime-loaded. Many dormant family modules are DTO-valid but unavailable to spawning/combat until registered.
- Spawn biome/tier availability lives in `src/backend/features/monsters/resources/spawn_config.py`, but spawn config does not register a family by itself.
- Natural monster weapons and armor are item base resources in `src/backend/features/items/resources/monster_equipment/natural.py` and are registered through `BASES_DB["monster_equipment"]`.

## Family Shape

Use `MonsterFamilyDTO` as the active contract. `monster_structs.py` is a typing aid and contains some legacy fields that DTO/runtime ignore.

Required top-level fields:

- `id`: stable lowercase snake case family id.
- `archetype`: one of `humanoid`, `beast`, `undead`, `construct`, `demon`, `unknown`.
- `organization_type`: one of `solitary`, `pack`, `gang`, `clan`, `legion`, `horde`, `swarm`.
- `hierarchy`: role buckets that reference variant ids.
- `variants`: mapping of variant key to variant object.

Effectively required for combat-ready families:

- `combat_profile`
- `skill_kit`
- `ability_map`
- `loot_profile`

Defaulted or optional fields:

- Top level: `default_tags`, `ability_map`, `combat_profile`, `skill_kit`, `loot_profile`.
- Variant: `extra_tags`, `min_tier`, `max_tier`, `fixed_loadout`, `skills`, `skill_overrides`, `ability_overrides`.

Do not rely on ignored or future-hook fields as runtime behavior. In particular, treat `ability_overrides`, `combat_profile.body_loadout`, `combat_profile.equipment_scaling`, and `combat_profile.modifier_formula` as unsafe/future hooks unless the runtime consumers are implemented in the same task.

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
- `base_stats` must include `strength`, `agility`, `endurance`, `intelligence`, `wisdom`, `men`, `perception`, `charisma`, and `luck`.
- `variant.skills` is a list of ability ids, not numeric catalog skill ids.

## Skills

Monster numeric skill values are stored in family resources under:

- `skill_kit.base`
- `skill_kit.role_bonus`
- `variant.skill_overrides`

Resource values may be written as design-scale `0..100`. Runtime normalizes with `_skill_value()` in `combat_profile.py`:

- Values greater than `1.0` become `value / 100.0`.
- Values less than or equal to `1.0` are treated as already-normalized floats.

Merge order:

1. Start with `skill_kit.base`.
2. Add `skill_kit.role_bonus[monster.role]`.
3. Apply `variant.skill_overrides`.

Use `None` in `skill_overrides` to remove an inherited skill. Use only real catalog ids such as `skill_unarmed`, `skill_archery`, or `skill_light_armor`; do not use ability ids or aggregate keys such as `survival`.

## Equipment And Loadouts

Runtime equipment resolution happens in `build_monster_combat_seed()` and `build_monster_combat_context()`.

Resolution order:

1. `family.combat_profile.natural_weapon_set`
2. `family.combat_profile.armor_class`
3. `variant.fixed_loadout` / generated `monster.loadout_ids`

Every referenced item id must resolve through `src.backend.features.items.resources.get_base_by_id()`. Missing ids are silently skipped by runtime, so validate references when editing families.

Natural weapons and natural armor are normal item base resources:

- Natural weapons use `type="monster_natural_weapon"` and usually `slot="main_hand"`.
- Natural armor uses `type="monster_natural_armor"` and usually `slot="chest_armor"`.
- Item `related_skill`, `skill_key`, `weapon_skill_key`, or `armor_skill_key` controls the combat loadout skill slot.
- Item `triggers` can add `main_hand_trigger` or `off_hand_trigger` when the resolved combat slot is a hand slot.

Humanoid variants usually use `fixed_loadout` for normal item bases. Beast families usually use natural weapon/armor ids in `combat_profile` and keep variant `fixed_loadout` empty.

## Abilities And Loot

Monster ability ids are stored in `variant.skills`, copied to generated `skills_snapshot`, then mapped through `family.ability_map`.

`ability_map` entries have:

- `mechanic`: combat mechanic id used in `loadout.abilities` and `known_abilities`.
- `presentation`: presentation id stored under `loadout.ability_presentations`.

If an ability id is missing from `ability_map`, runtime falls back to using the raw ability id as both mechanic and presentation. Avoid relying on that fallback for new families.

`ability_overrides` is accepted by DTO but is not consumed by the inspected runtime path.

`loot_profile` is declarative today. Tests and game catalog projections read it, but no active loot resolver was found. Current conventions:

- Humanoid equipment families use `loot_mode="equipment"`, `allowed_loadout_slots="full_humanoid"`, `equipment_drop_policy="fixed_loadout"`, and `drops_as_equipment=True`.
- Beast salvage families use `loot_mode="salvage"`, `allowed_loadout_slots="natural_only"`, `equipment_drop_policy="none"`, and `drops_as_equipment=False`.

## Combat Snapshot Compatibility

Generation in `ClanFactory` turns family resources into generated monster fields:

- `variant_key` from `variant.id`
- `role` from `variant.role`
- `threat_rating` from `variant.cost`
- `scaled_base_stats` from `variant.base_stats` multiplied by tier scaling
- `loadout_ids` from `variant.fixed_loadout`
- `skills_snapshot` from `variant.skills`
- `combat_seed` from `build_monster_combat_seed()`

Monster actor snapshots are built by `CharacterCombatCommitmentIntegration` using:

- `build_monster_vitals(monster)`
- `build_monster_combat_context(monster)`

`combat_seed` caches:

- `version`
- sorted monster/family/item tags
- normalized numeric `skills`
- resolved combat `loadout`
- `vitals`

Keep this compatibility in mind when changing family resources: persisted generated monsters may carry old `loadout_ids`, `skills_snapshot`, and `combat_seed` until regenerated.

## Naming Rules

- Use lowercase snake case for family ids, variant ids, ability ids, and item ids.
- Use catalog skill ids with the `skill_` prefix for numeric skills.
- Do not put geography in `default_tags`; biome/tier selection belongs in `spawn_config.py`.
- Keep ability ids distinct from catalog skill ids. Example: `attack_basic` is an ability id; `skill_unarmed` is a numeric skill id.

## Common Mistakes

- Adding a family module but not importing it into `ALL_FAMILIES_RAW`.
- Adding a family to `spawn_config.py` without registering it.
- Using `variant.skills` for catalog skill ids instead of ability ids.
- Referencing item ids that are not registered as item bases.
- Copying ignored fields from `monster_structs.py` such as `name_ru`, `description`, `combat_intro_text`, `_family_ref`, or `_archetype`.
- Assuming `loot_profile` currently performs runtime loot drops.
- Treating `ability_overrides`, `body_loadout`, `equipment_scaling`, or `modifier_formula` as active runtime behavior.
- Mixing `0..100` skill values and normalized `0.0..1.0` values without checking the boundary conversion.

## Known Docs/Code Disagreements

- `docs/game-design/rpg-rules/Monsters` does not exist in the current workspace.
- Skill design docs describe `0..100`, while runtime consumes normalized floats after boundary conversion.
- `combat_profile` validates fields that current runtime does not consume.
- `monster_structs.py` includes fields ignored by DTO/runtime, including presentation and service fields.
- Dormant family files validate but are not loaded by the current starter registry.
- `spawn_config.py` references dormant family ids that cannot spawn until those families are registered.

## Verification

Run focused monster runtime checks after family changes:

```powershell
.\.venv\Scripts\pytest.exe tests\backend\features\monsters\runtime\test_registry_and_combat_profile.py tests\backend\features\monsters\runtime\test_clan_factory.py --no-cov
```

Useful read-only registry check:

```powershell
.\.venv\Scripts\python.exe -c "from src.backend.features.monsters.resources import get_all_family_configs; print(sorted(get_all_family_configs()))"
```

When changing item ids or skill ids, also run focused item/catalog checks and search references:

```powershell
rg -n "skill_[a-z_]+|<item_id>|<family_id>|<variant_id>" src tests docs
```

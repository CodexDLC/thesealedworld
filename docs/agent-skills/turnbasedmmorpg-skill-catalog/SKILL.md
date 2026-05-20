---
name: turnbasedmmorpg-skill-catalog
description: Skill catalog ownership and safety rules for TurnBasedMMORPG. Use before adding, renaming, validating, displaying, or consuming skills across catalog resources, character sessions, actor snapshots, combat, exploration, crafting, inventory, scenarios, items, monsters, or status UI.
---

# TurnBasedMMORPG Skill Catalog

## First Reads

Read these before changing skill ids, skill definitions, skill value math, or any consumer that stores or displays skills:

- `docs/agent-skills/turnbasedmmorpg-project/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-backend/SKILL.md`
- `docs/game-design/rules/skills/catalog_reference.md`
- `docs/game-design/rules/skills/progression_reference.md`
- `docs/game-design/rules/skills/combat_runtime_reference.md`
- `src/backend/features/game_catalog/skills`
- `src/backend/features/character/dto/modifiers.py`
- `src/shared/schemas/modifier_dto.py`
- `tests/backend/features/game_catalog/skills`

For runtime consumers, also inspect the relevant feature slice before editing:

- Character session/snapshot: `src/backend/features/character/schemas/session.py`, `src/backend/features/character/managers/session.py`, `src/backend/features/character/runtime/combat_actor_input.py`, `src/backend/features/character/runtime/combat_math_model.py`
- Combat: `src/backend/features/combat/dto/actor.py`, `src/backend/features/combat/runtime/engine`
- Exploration/encounter: `src/backend/features/exploration/services`, `src/backend/features/exploration/runtime`
- Scenario rewards: `src/backend/features/scenario/resources/json`, `src/backend/features/scenario/engine/formatter.py`
- Items/inventory: `src/backend/features/items/resources`, `src/shared/schemas/item.py`
- Monsters: `src/backend/features/monsters/resources/families`
- Status UI: `src/backend/features/character/services/status_service.py`, `src/frontend/templates/game/components/panel/widgets/skill_groups.html`

## Ownership

The canonical skill catalog is owned by `src/backend/features/game_catalog/skills`.

- Skill definitions live in `resources/definitions/*.py`.
- `SkillDefinitionDTO`, `SkillCategory`, `SkillGroup`, and `SkillUiGroup` live in `dto/catalog.py`.
- `SkillCatalogService` is the read API for catalog lookups and public text projection.
- `resources/contracts.py` owns surface-specific key lists for actor snapshots, encounters, crafting, and inventory.
- `tests/backend/features/game_catalog/skills/test_catalog_service.py` is the primary guard that catalog ids, groups, UI groups, and surface contracts stay coherent.

Do not move the catalog into `shared`. Shared code may contain compatibility DTOs, but the catalog itself is backend feature-owned.

## Current Skill IDs

Use these exact ids unless a rename task explicitly updates every reference.

Combat:

- Weapon Mastery: `skill_swords`, `skill_fencing`, `skill_polearms`, `skill_macing`, `skill_archery`, `skill_unarmed`
- Tactical: `skill_one_handed`, `skill_two_handed`, `skill_shield_mastery`, `skill_dual_wield`
- Armor: `skill_light_armor`, `skill_medium_armor`, `skill_heavy_armor`
- Combat Support: `skill_parrying`, `skill_anatomy`, `skill_tactics`

Crafting:

- `skill_first_aid`, `skill_weapon_craft`, `skill_armor_craft`, `skill_jewelry_craft`, `skill_alchemy`, `skill_engineering`, `skill_artifact_craft`

World:

- Gathering: `skill_mining`, `skill_herbalism`, `skill_skinning`, `skill_woodcutting`, `skill_hunting`, `skill_archaeology`
- Survival: `skill_taming`, `skill_adaptation`, `skill_scouting`, `skill_pathfinder`

Social:

- Trade: `skill_accounting`, `skill_brokerage`, `skill_contracts`, `skill_trade_relations`
- Leadership: `skill_leadership`, `skill_organization`, `skill_team_spirit`, `skill_egoism`

## Naming Rules

Every skill id must be lowercase snake case and must start with `skill_`.

The prefix is mandatory because:

- `load_skill_definitions()` rejects unprefixed ids.
- Catalog tests assert every skill id is prefixed.
- Combat context derives weapon class by stripping `skill_`, for example `skill_swords` becomes `swords`.
- Items, scenario rewards, actor snapshots, monster kits, combat loadout, and status UI use `skill_*` as stable catalog keys.

Do not add aggregate ids such as `survival`, category ids such as `crafting`, or ability-style ids such as `skill_power_strike` to the skill catalog unless they are real catalog skills and all references/tests are updated.

## Value Scale

Internal skill values are normalized floats in `0.0..1.0`.

- Store active character session and actor snapshot values as normalized floats.
- Runtime formulas should consume normalized values directly.
- UI, design docs, and player-facing text may display the same value as `0..100`; that is a presentation conversion only.
- If a formula or doc says `Skill / 100`, verify whether it is legacy `0..100` wording before copying it into runtime code.

Known scale risks:

- Some older combat formulas still divide skill values by `100.0`.
- Some design docs describe skill progression as `0..100`.
- New code must not mix `0.0..1.0` and `0..100` without an explicit conversion at the boundary.

## UI Display Rule

`display_value = round(skill_value * 100, 1)` — UI and player-facing text shows `0..100` (percent of mastery), the internal representation is always `0.0..1.0`.

Never pass raw `0.0..1.0` values to UI templates. Never store `0..100` display values in Redis or DTOs.

## Progression Model

Skills grow via a Ultima Online–style formula: using a skill awards XP, but growth slows as the skill value rises (diminishing returns):

```
delta = (base_power × global_rate × rate_mod) / (1 + current_skill × effective_wall)
```

- `global_rate = 0.00005` — current alpha base growth speed per action
- `effective_wall = global_wall × wall_mod` — difficulty ceiling (default `100.0`)
- `current_skill` — current normalized value (`0.0..1.0`)
- At `skill = 1.0` the denominator is `1 + 100 = 101`, delta approaches zero

Implementation: `src/backend/core/calculators/skill_progression_calculator.py` → `SkillProgressionCalculator.calculate_delta()`.

`base_power` is derived from character attribute weights defined on the `SkillDTO` (`stat_weights`). `action_power` is provided per action (e.g., combat exchange grants `1.0`, crafting may vary).

Do not implement custom progression math. Use `SkillProgressionCalculator` for all XP delta computation.

## Combat Catalog Integration

Weapon mastery skills link directly to the combat catalog via `weapon_class`:

- `context_builder.py` sets `ctx.flags.meta.weapon_class = skill_key.replace("skill_", "")` (e.g., `"skill_swords"` → `"swords"`)
- Basic exchange catalog keys follow the pattern `f"skill_{weapon_class}.{source_type}"` (e.g., `"skill_swords.main_hand"`)
- Basic exchange catalog module: `src/backend/features/game_catalog/combat/resources/basic_exchanges/`

When adding a new weapon mastery skill, also add a corresponding basic exchange entry in `basic_exchanges/definitions/weapon_mastery.py` with event texts for `use`, `hit`, `crit`, `miss`, `dodge`, `parry`, `block`.

## Surface Contracts

Keep `src/backend/features/game_catalog/skills/resources/contracts.py` in sync whenever a skill is added, renamed, removed, or starts/stops affecting a surface.

Current surfaces:

- `actor_snapshot`: combat skills plus `skill_adaptation`.
- `encounter`: `skill_scouting`, `skill_pathfinder`, `skill_hunting`, `skill_taming`.
- `crafting`: `skill_first_aid`, `skill_weapon_craft`, `skill_armor_craft`, `skill_jewelry_craft`, `skill_alchemy`, `skill_engineering`, `skill_artifact_craft`.
- `inventory`: combat equipment skills plus `skill_parrying`, `skill_weapon_craft`, `skill_armor_craft`, `skill_jewelry_craft`, `skill_engineering`.

Exploration/encounter should use explicit `skill_*` keys from the encounter contract. Treat aggregate reads such as `skills.get("survival")` as legacy or incorrect unless the project owner explicitly approves an aggregate contract.

## DTO Contracts

The active feature-owned DTO contract for character modifiers is:

- `src/backend/features/character/dto/modifiers.py`

The shared modifier DTO is legacy compatibility:

- `src/shared/schemas/modifier_dto.py`

Do not extend `src/shared/schemas/modifier_dto.py` as the canonical source of truth. If a consumer still imports the shared DTO, inspect that path carefully and prefer a scoped migration or compatibility note instead of spreading the legacy contract further.

## Reference Surfaces

When adding or renaming a skill, search beyond the catalog.

- Scenarios: JSON resources use `skills_queue` entries such as `push:skill_swords`; formatter exposes `catalog: skills` links.
- Monsters: family resources use `skill_kit` and `skill_overrides`.
- Items and inventory: item resources and shared item schemas use `related_skill`, `skill_key`, `weapon_skill_key`, or `armor_skill_key`.
- Combat loadout: `CharacterCombatActorInputBuilder` maps equipped items into combat layout skill ids; combat context consumes those layout ids.
- Actor snapshots: character snapshots flatten active session skills into `combat.skills`.
- Status UI: `CharacterStatusService` groups session skills by catalog `ui_group` and emits catalog links.
- Progression/persistence: character session and skill repository code store unlocked skill ids and values under `$.skills.<skill_key>`.

Use `rg -n "skill_[a-z_]+" src tests docs` as the first broad reference scan.

## Add Or Rename Workflow

For a new skill:

1. Add the `SkillDTO` in the correct `resources/definitions/*.py` file, or create a new definition file only if the existing UI/domain groups do not fit.
2. Add the definition group to `SKILL_GROUPS` if a new file was created.
3. Choose `category`, `group`, and `ui_group` deliberately:
   - `category`: broad `combat` vs `non_combat`.
   - `group`: storage/domain group, one of `combat`, `world`, `crafting`, `social`.
   - `ui_group`: display grouping such as `weapon_mastery`, `survival`, or `trade`.
4. Update `SKILL_SURFACE_CONTRACTS` if any runtime surface needs the skill.
5. Update active DTO fields only when typed combat/status consumers require a fixed field.
6. Update scenario rewards, monster kits, item `related_skill` fields, combat loadout mapping, status UI expectations, and docs as needed.
7. Update catalog tests so the documented key set matches the actual catalog.

For a rename:

1. Treat it as a breaking catalog migration.
2. Replace every reference in definitions, tests, surface contracts, scenarios, monsters, items, snapshots/loadout code, status UI, and docs.
3. Decide whether persisted active sessions or DB skill progress rows need a migration or compatibility alias.
4. Verify no old id remains with `rg -n "<old_skill_id>" src tests docs`.

## Known Docs/Code Disagreements

Record these when planning skill work:

- Some docs use `Skill / 100`; canonical internal runtime/storage values are normalized `0.0..1.0`.
- Some combat resolver paths still divide by `100.0`; inspect before relying on those formulas.
- Exploration currently has legacy aggregate reads such as `skills.get("survival")`; intended contract is explicit `skill_*` keys.
- `docs/game-design/rules/skills/catalog_reference.md` preserves the reviewed
  current catalog weights; do not resurrect old generic rows that have no
  catalog id.
- Scenario designer docs mention `skill_power_strike`, which is not a catalog skill.
- Combat still imports `src/shared/schemas/modifier_dto.py` in some places even though the active owner is the character feature DTO.

## Common Mistakes

- Adding a skill id without the `skill_` prefix.
- Updating design docs but not catalog tests.
- Adding an id to scenarios, monsters, or items before it exists in `SkillCatalogService`.
- Treating `ui_group` as the storage/domain group.
- Using aggregate keys like `survival` in runtime checks.
- Assuming player-facing `0..100` display values are stored internally.
- Extending the shared legacy modifier DTO as if it were the active contract.
- Renaming a skill without checking scenario resources, monster resources, item `related_skill`, combat loadout, actor snapshots, and status UI.

## Verification

Run the narrowest relevant tests first:

```powershell
.\.venv\Scripts\pytest.exe tests\backend\features\game_catalog\skills --no-cov
.\.venv\Scripts\pytest.exe tests\backend\features\scenario\test_awakening_rift_catalog_contract.py --no-cov
.\.venv\Scripts\pytest.exe tests\backend\features\character\runtime tests\backend\features\character\test_status_service.py --no-cov
```

If scenarios, monsters, or items were touched, also run their catalog/contract tests or add focused tests before finishing.

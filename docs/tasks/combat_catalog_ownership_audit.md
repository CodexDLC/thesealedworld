# Combat Catalog Ownership Audit

Date: 2026-05-03

## Scope

Checked combat dictionaries/resources ownership after moving the combat catalog source of truth to `src/backend/features/game_catalog/combat/resources/**`.

No new combat mechanics, balance values, effects, abilities, feints, triggers, gifts, or taxonomy text were added.

## Inventory Table

| old path | new path | catalog key/id | resource type | technical status | descriptive status | runtime consumers | notes |
|---|---|---:|---|---|---|---|---|
| `src/backend/features/combat/resources/abilities/**` | `src/backend/features/game_catalog/combat/resources/abilities/**` | 4 ids | abilities | `OK_MOVED` | base `name_ru`/`description_ru` present; taxonomy/event variants missing | `AbilityService` via `CombatCatalogIntegrator.get_ability`; public bootstrap projection | Old path absent. Technical fields kept: cost, source/type, target, target_count, raw mutations, pipeline preset/flags, triggers, effects, override damage. |
| `src/backend/features/combat/resources/effects/**` | `src/backend/features/game_catalog/combat/resources/effects/**` | 23 ids | effects | `OK_MOVED` | base `name_en`/`name_ru`/`description` present; taxonomy/event variants missing | `AbilityService` via `CombatCatalogIntegrator.get_effect`; `EffectFactory` consumes typed config; public bootstrap projection | Old path absent. Technical fields kept: type, duration, resource impact, raw modifiers, control logic, tags. |
| `src/backend/features/combat/resources/feints/**` | `src/backend/features/game_catalog/combat/resources/feints/**` | 8 ids | feints | `OK_MOVED` | base `name_ru`/`description_ru` present; taxonomy/event variants missing | `FeintService` via integrator; `AbilityService` via integrator; public bootstrap projection | Old path absent. Technical fields kept: cost, target, target_count, raw mutations, pipeline mutations, triggers, effects, override damage. |
| `src/backend/features/combat/resources/triggers/**` | `src/backend/features/game_catalog/combat/resources/triggers/**` | 19 ids | triggers | `OK_MOVED` | base `name_ru`/`description_ru` present; taxonomy/event variants missing | `CombatResolver` via `CombatCatalogIntegrator.get_trigger_rule`; public bootstrap projection | Old path absent. Technical fields kept: id, event, chance, mutations. |
| `src/backend/features/combat/resources/gifts/**` | `src/backend/features/game_catalog/combat/resources/gifts/**` | 12 ids | gifts | `OK_MOVED` | base `name_ru`/`description` present; taxonomy/event variants missing | public bootstrap projection; adapter exposes `get_gift` | Old path absent. Technical fields kept: gift_id, school, role, abilities; XP config remains in game_catalog gift resources. |
| n/a | `src/backend/features/game_catalog/combat/resources/common/**` | targeting enums | common technical support | `OK_MOVED` | not descriptive | ability/feint schemas | Shared resource-local targeting enum. |
| n/a | `src/backend/features/game_catalog/combat/resources/catalog.py` | public text projection | catalog projection | `OK_MOVED` | emits fallback `DATA_MISSING: combat_description:<id>` if base description is absent | `GameCatalogBootstrapService`, tests, frontend catalog bootstrap | Public projection exposes safe text and selected public metadata only, not full runtime config. |

## Runtime Consumers

| file | dictionary used | id/config needed | technical/descriptive usage | direct game_catalog import | old combat.resources import | adapter replacement |
|---|---|---|---|---|---|---|
| `src/backend/features/combat/runtime/engine/ability_service.py` | abilities, feints, effects, pipeline presets | `ability_id`, `feint_id`, cost, raw mutations, pipeline preset/flags, triggers, effects, override damage, effect ids/params | technical | schema type imports only after fix; runtime lookup via integrator | no | done for ability, feint, effect, pipeline preset |
| `src/backend/features/combat/runtime/engine/feint_service.py` | feints | `feint_id`, token cost, `name_ru` for dashboard button fallback | technical plus temporary base label | no | no | already uses `CombatCatalogIntegrator.get_feint` |
| `src/backend/features/combat/runtime/engine/resolver.py` | trigger rules | trigger id, event, chance, mutations | technical | no after fix | no | done via `CombatCatalogIntegrator.get_trigger_rule` |
| `src/backend/features/combat/runtime/engine/effect_factory.py` | effect config schema | `effect_id`, duration, resource impact, raw modifiers, control logic, tags | technical | schema type imports | no | lookup already happens before factory; no behavior change needed |
| `src/backend/features/combat/dto/actor.py` | control schema | `ControlInstructionDTO` for active effect state | technical schema | schema import | no | `NEEDS_DECISION`: schema ownership can later move to a neutral DTO package if direct schema imports are disallowed |
| `src/backend/features/combat/dto/response.py` | control schema | `ControlInstructionDTO` for active effect state | technical schema | schema import | no | `NEEDS_DECISION`: duplicate/legacy DTO surface should be reconciled separately |
| `src/backend/features/combat/integrations/catalog_integrator.py` | abilities, effects, feints, gifts, triggers, presets | read-only runtime dictionary access | technical adapter | yes, allowed | no | intended boundary |

## Technical Layer Status

All current technical entries loaded successfully:

- abilities: `fireball`, `heal`, `stone_skin`, `true_strike_spell`
- effects: `dot_poison`, `dot_bleed`, `dot_burn`, `hot_regen_hp`, `hot_regen_en`, `buff_str`, `buff_dex`, `buff_int`, `buff_end`, `buff_armor`, `buff_evasion`, `buff_accuracy`, `buff_crit`, `buff_phys_dmg`, `debuff_str`, `debuff_armor`, `debuff_evasion`, `debuff_accuracy`, `stun`, `sleep`, `knockdown`, `disarm`, `silence`
- feints: `piercing_thrust`, `shield_bash`, `cleave`, `true_strike`, `power_attack`, `defensive_strike`, `sand_throw`, `low_blow`
- triggers: `true_strike`, `rage_on_miss`, `bleed_on_crit`, `stun_on_crit`, `heavy_strike_on_crit`, `true_crit`, `unblockable_crit`, `piercing_crit`, `counter_on_dodge`, `disarm_on_parry`, `counter_on_parry`, `shield_bash_on_block`, `stun_on_hit`, `bleed_on_hit`, `evasive_shot`, `style_1h_flow`, `style_2h_ignore`, `style_shield_reflect`, `style_dual_extra`
- gifts: `gift_true_fire`, `gift_inferno`, `gift_dragon_flame`, `gift_calm_water`, `gift_typhoon`, `gift_venom_blood`, `gift_paladin`, `gift_purifier`, `gift_shadow_assassin`, `gift_necrosis`, `gift_beastmaster`, `gift_thorns`

No `MISSING_TECHNICAL` or `BEHAVIOR_CHANGED` entries were found in the current source tree. Because the old `src/backend/features/combat/resources/**` path is absent from the working tree and absent from `HEAD`, comparison is limited to current import/contract/runtime behavior and tests.

## Descriptive Layer Status

Base descriptive fields exist for every current technical id:

- abilities and feints use `name_ru` and `description_ru`
- effects use `name_en`, `name_ru`, and `description`
- triggers use `name_ru` and `description_ru`
- gifts use `name_ru` and `description`

Missing for all current ids:

- dedicated `CatalogDescriptionDTO`
- stable full catalog key such as `combat.ability.fireball`
- `display_name`, `short_description`, `long_description`, `ui_label`, `tooltip`
- `event_texts` for `hit`, `crit`, `miss`, `block`, `parry`, `dodge`, `apply_effect`, `expire_effect`, `use_ability`, `use_feint`
- taxonomy variants for `beast`, `arachnid`, `humanoid`

Recommended placeholder shape for future split, without changing mechanics:

```python
{
    "key": "combat.ability.fireball",
    "technical": CombatAbilityTechnicalDTO(...existing technical fields...),
    "descriptive": CatalogDescriptionDTO(
        display_name="TODO_FROM_EXISTING_NAME_OR_MISSING",
        short_description="TODO_MISSING_DESCRIPTION",
        long_description="TODO_MISSING_DESCRIPTION",
        event_texts={},
        taxonomy_variants={
            "beast": None,
            "arachnid": None,
            "humanoid": None,
        },
    ),
}
```

Players should resolve through the `humanoid` taxonomy variant. If a variant is absent, fallback should be `generic` or `humanoid`, with the missing variant recorded rather than invented.

## Bootstrap and Public Projection

`GameCatalogBootstrapService` receives combat catalogs from `CombatResourceCatalogService` in game_catalog and includes:

- `abilities`
- `effects`
- `feints`
- `triggers`
- `gifts`

The bootstrap returns public text projection, not full runtime config. `catalog.py` currently includes title/description plus selected public metadata fields: `source`, `type`, `target`, `target_count`, `event`, `chance`, `school`, `role`, `duration`, `tags`.

## Logs and Dashboard

`CombatViewService` builds dashboard state: hero, target, allies, enemies, status, active effects, feints, available actions, and catalog refs.

Current dashboard code does not render artistic combat text from combat dictionaries. `parse_logs` parses existing raw log JSON/text into DTO events. A future text layer should be separate, for example `CombatLogTextService` or `CombatEventTextResolver`, and should accept technical event/result fields before resolving text through descriptive catalog entries.

## Imports

Checked commands:

- `rg "src\.backend\.features\.combat\.resources" src tests`: no matches
- `rg "features/combat/resources|features\\combat\\resources" src tests`: no matches
- `rg "src\.backend\.features\.game_catalog\.combat\.resources" src/backend/features/combat tests/backend/features/combat`: only integrator, schema type imports, and tests remain

Remaining direct game_catalog imports inside combat:

- `catalog_integrator.py`: allowed adapter boundary
- `ability_service.py`, `effect_factory.py`, `dto/actor.py`, `dto/response.py`: schema/type imports only; `NEEDS_DECISION` if schema ownership must also be hidden behind a neutral package
- combat tests: direct imports validate resource availability and public projection

Removed during this audit:

- direct runtime import of `PIPELINE_PRESETS`
- direct runtime import of `TRIGGER_RULES_DICT`

## Verification

- `uv run ruff check src/backend/features/game_catalog/combat src/backend/features/game_catalog src/backend/features/combat`: passed
- `uv run pytest tests/backend/features/combat tests/backend/features/game_catalog --no-cov`: 20 passed

Initial sandboxed `uv` attempts failed with interpreter permission denied; the same commands passed after escalation.

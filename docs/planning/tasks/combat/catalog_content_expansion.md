# Combat Catalog Content Expansion

Status: expected.

The combat catalog already lives under
`src/backend/features/game_catalog/combat/resources/**`. This task tracks future
content expansion on top of the existing catalog, not ownership migration.

## Goals

- Expand player-facing descriptions for combat catalog entries.
- Add richer combat log text templates and fragments.
- Add new feints, weapon techniques, item actions, triggers, and related text.
- Keep runtime technical data and descriptive presentation data separated.

## Current Baseline

The active combat catalog contains resources for:

- abilities;
- effects;
- feints;
- triggers;
- gifts;
- basic exchanges;
- combat item actions;
- combat tokens;
- combat text templates and fragments.

Combat runtime should access catalog data through
`CombatCatalogIntegrator` where possible. Public/frontend-facing bootstrap data
should expose safe text/projection data, not full runtime configuration.

## Content Work

- [ ] Review current ability, effect, feint, trigger, gift, item-action, token,
      and basic-exchange descriptions.
- [ ] Add missing `ui_label`, tooltip, short description, and long description
      where the catalog contract supports them.
- [ ] Expand event text for combat outcomes: hit, crit, miss, block, parry,
      dodge, apply effect, expire effect, use ability, use feint, death.
- [ ] Add body/taxonomy variants for at least humanoid and beast targets where
      combat logs need different wording.
- [ ] Ensure missing variants fall back through a clear generic/humanoid path
      instead of inventing text at runtime.

## New Combat Options

- [ ] Design new feints and weapon techniques from the current combat design
      direction.
- [ ] Add catalog entries with technical data and descriptive text together.
- [ ] Add or extend trigger text for new weapon and style triggers.
- [ ] Add tests that new ids are registered, projected, and usable by runtime
      integrators.

## Non-Goals

- Do not move catalog ownership back into `combat`.
- Do not expose full runtime config through public bootstrap data.
- Do not add new combat mechanics without matching runtime tests.

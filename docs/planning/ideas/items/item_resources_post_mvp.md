# Item Resources Post-MVP Roadmap

Status: idea source, not a source of truth.

This document is preserved as a collection of possible future item-system
directions. It was written before the current item implementation settled and
must be revised against real code before any phase is treated as roadmap or
implementation work.

This document is the post-MVP development layer for the item system. It is written as a stable roadmap source that can later be converted into a website roadmap page.

## MVP Baseline

Status: closed for MVP unless playtests expose a blocker.

The MVP item layer includes:

- base item catalog with cleaned combat semantics;
- material-driven tier scaling through `tier_mult`;
- deterministic tier-0/common trash item text;
- generated item mechanics source shape with `implicit_bonuses`, `material`, `affixes`, and reserved `sockets`;
- affix catalog, modifier contracts, pools, and 3/4-affix bundles;
- actor assembly projection from item mechanics into combat math;
- inventory tooltip projection for base and rolled affix data;
- first scenario rewards aligned with tier-0/common starter gear.

MVP rules that should remain stable:

- common/tier-0 starter items have no affixes and no LLM text calls;
- material is the only mechanical tier multiplier;
- rarity/grade controls affix container and label, not a second power multiplier;
- bundles are references to single affixes and own no math values;
- old flat `bonuses` is not canonical item storage.

## Phase 1 - Balance And Admin Levers

Goal: make generation tunable without code edits.

Planned work:

- expose material tier multipliers in server/admin settings;
- expose global affix step count and per-affix roll profiles for testing;
- add generation preview tools for item families, tiers, grades, and sources;
- add balance reports for average rolled values by item type and material tier;
- add safeguards that prevent probability affixes from drifting beyond MVP ranges.

Website roadmap label: `Balancing tools`.

## Phase 2 - Crafting Inputs

Goal: reuse the item generator for crafting while keeping crafting rules separate from loot.

Planned work:

- introduce recipe validation as a source layer before item generation;
- let recipes resolve `base_id`, `material_id`, grade, source tags, and forced constraints;
- keep the generator shared between loot and crafting;
- add basic MVP recipes only after the loot loop feels stable;
- record crafted source context for AI text and future item history.

Website roadmap label: `Crafting foundation`.

## Phase 3 - Sockets, Gems, And Inserts

Goal: activate the reserved `sockets` mechanics key.

Planned work:

- define socket capacity rules from item family/material/source;
- add socket insert catalog using the same modifier contract layer as affixes;
- compile socket modifiers into actor/world projections through a separate applier;
- support socket replacement/removal costs later through crafting;
- keep sockets visually separate from affixes in item UI.

Website roadmap label: `Sockets and gems`.

## Phase 4 - Affix Economy

Goal: give players long-term item chasing without changing the core storage shape.

Planned work:

- add affix value reroll;
- add affix replacement;
- add bundle replacement or bundle injection for rare sources;
- add locked affix rules for special items;
- introduce powder/reagent resources mapped to affix groups;
- support item grade upgrade without using grade as a direct power multiplier.

Website roadmap label: `Item reroll and upgrades`.

## Phase 5 - Build-Style Bundles

Goal: expand item identity through rare 3/4-affix style packages.

Planned work:

- create separate bundle families for weapons, armor, shields, garments, belts, and accessories;
- expand style directions such as duelist, bulwark, bleed, survival, scout, armor tank, evasion tank, and dot damage;
- keep bundles as affix-id lists only;
- add source constraints for boss, clan, biome, and rift origin;
- tune bundle frequency so random singles can still accidentally create interesting builds.

Website roadmap label: `Build-style loot`.

## Phase 6 - Artifact And Boss Item Layer

Goal: give major world sources recognizable item identities.

Planned work:

- define forced bundles and unique pools for bosses/world entities;
- allow artifacts to force narrative text even when normal tier rules would skip AI;
- add unique display tags and source history;
- reserve room for special trigger/passive behavior, but keep numeric bonuses on modifier contracts;
- create four major world-entity item families after their gameplay identity is stable.

Website roadmap label: `Artifacts and boss loot`.

## Phase 7 - Material Identity After MVP

Goal: decide whether materials remain pure multipliers or gain base-block identity.

Candidate directions:

- leather biases evasion, heat/nature survival, and light armor identity;
- metal biases armor, shield guard, durability, and evasion penalties;
- cloth biases environment, magic, status, and garment utility;
- wood biases shields, staffs, bows, guard, nature, and accuracy.

Rule if implemented:

- material bonuses belong to the base block, not to affixes;
- material bonuses must not duplicate the affix economy;
- material identity should help item feel, not replace build choices.

Website roadmap label: `Material identity`.

## Phase 8 - World Modifiers

Goal: activate non-combat item modifiers in active character and world checks.

Planned work:

- create world modifier receiver/projection separate from combat-only DTOs;
- consume affixes such as travel speed, scouting, pathfinding, crafting speed, trade bonus, and resource find;
- let garments, belts, and accessories become primary world-modifier carriers;
- keep unsupported world affixes catalog-ready but filtered until consumers exist.

Website roadmap label: `World item bonuses`.

## Phase 9 - Magic, Vampiric, And Elemental Affixes

Goal: enable reserved affix groups when combat systems can consume them cleanly.

Planned work:

- wire magic/elemental resistance and penetration into combat formulas;
- enable vampiric chance/power only after hit resolution and healing ownership are stable;
- add biome/source constraints for elemental affixes;
- keep these affixes out of random item pools until balance tests are ready.

Website roadmap label: `Magic and vampiric affixes`.

## Phase 10 - Item Text And History

Goal: make generated item text feel tied to the world without making the LLM own mechanics.

Planned work:

- enrich `source_context` with monster family, clan, biome, anchor, location, and scenario data;
- add batch generation or queued generation for high-volume loot;
- store compact item name/description and AI status only;
- add item history snippets for artifacts and crafted items;
- keep validation in code, not in model self-check fields.

Website roadmap label: `World-aware item text`.

## Website Roadmap Card Shape

Use this compact shape when converting the roadmap to a site section:

```json
{
  "id": "item-sockets",
  "title": "Sockets and gems",
  "status": "post_mvp",
  "summary": "Activate the reserved sockets layer so gems and inserts can add modifier-contract bonuses without mixing into affixes.",
  "depends_on": ["item-mvp-baseline", "crafting-foundation"],
  "player_value": "More long-term item customization and cleaner upgrade goals."
}
```

Suggested statuses:

- `mvp_closed`
- `post_mvp`
- `planned`
- `blocked_by_system`
- `research`

## Deferred Questions

- How many reroll currencies are needed without making the economy noisy?
- Should artifact items be upgradeable or fixed world records?
- Should material identity stay subtle, or become a major build axis?
- Which world modifiers matter first: travel, scouting, crafting, or trade?
- When should magic/vampiric affixes enter random pools instead of boss-only sources?

# Lore and Interface Source Map

Use this map to load only the files relevant to the current task.

## RPG Rules

Root: `docs/game-design/`

- `library/rpg/attributes.md` - player-facing attribute library source:
  Body, Core, Sensor; Strength, Agility, Endurance, Intellect, Memory, Mental,
  Perception, Projection, Prediction.
- `rules/attributes/technical_reference.md` - runtime attribute mapping,
  player formulas, monster profile overrides, and future/non-runtime ideas.
- `library/rpg/skills/README.md` - player-facing skills overview source for
  future library articles and tooltip copy.
- `library/rpg/skills/combat.md` - player-facing weapon, tactical style, armor,
  and combat support skill identity.
- `library/rpg/skills/crafting.md` - player-facing crafting skill identity.
- `library/rpg/skills/world.md` - player-facing gathering and survival skill identity.
- `library/rpg/skills/social.md` - player-facing trade and leadership skill identity.
- `rules/skills/catalog_reference.md` - current skill catalog, ui groups, weights,
  and progression modifiers.
- `rules/skills/progression_reference.md` - current skill progression formula,
  runtime scale, and alpha tuning notes.
- `rules/skills/combat_runtime_reference.md` - current combat skill runtime hooks
  and future design boundaries.
- `rpg-rules/Gifts/README.md` - older gift fantasy and progression source material.
- `domains/gifts/README.md` - reviewed Gifts and Symbiote concept source.
- `library/rpg/items.md` - player-facing item model library source.
- `rules/items/item_model_reference.md` - item source model, material, grade,
  implicit bonus, affix, socket, projection, and text reference.
- `rules/items/weapon_type_source.md` - weapon type design and catalog expansion
  source; verify ids against runtime catalogs before implementation.
- `rules/modifiers/modifier_vocabulary.md` - current modifier vocabulary for
  vitals, weapon stats, defenses, elemental/status effects, special modifiers,
  world stats, and active aliases.
- `rules/modifiers/actor_mapper_reference.md` - current mapper/waterfall layer
  reference for actor raw math, item affixes, and monster profile additions.
- `library/rpg/modifiers.md` - player-facing modifier explanation source for
  future library articles and tooltip copy.

## Designer Docs

Root: `docs/game-design/designer/`

- `world/00_world_bible.md` - main world/lore bible.
- `world/01_world_vision.md` - high concept and setting.
- `world/02_geography_and_topology.md` - geography, location graph, coordinate
  scale, explicit region exits, D4 capital layout, and gated world transitions.
- `world/03_threat_and_anchors.md` - threat fields and anchor concepts.
- `world/04_interaction_and_scouting.md` - exploration, scouting, navigation.
- `world/05_game_loops.md` - survival loop, expedition, rift, hub.
- `world/06_quests_and_narrative.md` - quest and NPC narrative direction.
- `world/07_group_dynamics.md` - groups, leadership, loot, XP sharing.
- `world/08_monsters_and_actors.md` - monster behavior and group encounters.
- `world/09_narrative_and_destiny.md` - weighted stats and scenario resonance.
- `combat/` - combat vision, tactical layer, mechanics philosophy, combat
  entities, weapon triggers, and designer combat config ideas.
- `rpg/` - player-facing RPG philosophy parallel to `rpg-rules/`.
- `economy/` - resource, item, inventory, risk, and crafting fantasy.
- `scenarios/01_zero_shard.md` - awakening scenario seed.

## Interface and Drafts

Root: `docs/game-design/interface/`

- `ui_philosophy_draft.md` - dual-message interface idea.
- `handler_and_ui_standard.md` - old handler/UI guidance; use only for intent.
- `design_doc_helper.md` - library/help interface concept.

Reviewed Gifts drafts were migrated into `docs/game-design/domains/gifts/`.
Original source drafts are archived under
`docs/archive/game-design/old-drafts/gifts/`.

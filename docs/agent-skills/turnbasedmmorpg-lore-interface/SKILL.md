---
name: turnbasedmmorpg-lore-interface
description: Lore, RPG philosophy, skill/attribute meaning, world design, scenario intent, and interface-intent navigation for TurnBasedMMORPG. Use when changing or designing player-facing lore, attributes, skills, gifts, combat concepts, RPG progression, scenario text, world content, status UI copy, game interface concepts, or any feature where old Telegram_Bot_RPG design docs should guide current implementation.
---

# TurnBasedMMORPG Lore Interface

## First Reads

Read:

- `docs/game-design/README.md`
- `docs/agent-skills/turnbasedmmorpg-lore-interface/references/source-map.md`

Then read only the specific source files needed for the task.

For frontend implementation, also use `turnbasedmmorpg-frontend` and
`turnbasedmmorpg-design-system`.

For backend contracts, services, or repositories, also use
`turnbasedmmorpg-backend`.

For end-to-end feature work, also use `turnbasedmmorpg-feature-slice`.

## Core Rule

Use `docs/game-design/` as design intent, not as current code architecture.

The old documents explain what attributes, skills, gifts, world systems, combat
ideas, and interface concepts mean. They do not override current schemas,
routers, DTOs, templates, CSS, service boundaries, or Redis/event rules.

## Navigation

Use these entry points:

- Attributes and naming rationale:
  `docs/game-design/library/rpg/attributes.md`
- Attribute runtime mapping:
  `docs/game-design/rules/attributes/technical_reference.md`
- Skill philosophy and skill families:
  `docs/game-design/library/rpg/skills/README.md`
- Attribute weights behind skills:
  `docs/game-design/rules/skills/catalog_reference.md`
- Skill progression concept:
  `docs/game-design/rules/skills/progression_reference.md`
- Combat skill groups:
  `docs/game-design/library/rpg/skills/combat.md`,
  `docs/game-design/rules/skills/combat_runtime_reference.md`
- Crafting, gathering, social, and survival skills:
  `docs/game-design/library/rpg/skills/crafting.md`,
  `docs/game-design/library/rpg/skills/world.md`,
  `docs/game-design/library/rpg/skills/social.md`
- Gifts and magic schools:
  `docs/game-design/rpg-rules/Gifts/README.md`
- Modifier vocabulary:
  `docs/game-design/rules/modifiers/modifier_vocabulary.md`
- Actor mapper reference:
  `docs/game-design/rules/modifiers/actor_mapper_reference.md`
- World, lore, and scenario design:
  `docs/game-design/designer/world/`,
  `docs/game-design/designer/scenarios/`
- World topology, region exits, D4 capital layout, and coordinate scale:
  `docs/game-design/designer/world/02_geography_and_topology.md`
- Combat feel and tactical UX:
  `docs/game-design/designer/combat/`
- Economy and inventory fantasy:
  `docs/game-design/designer/economy/`
- Interface intent:
  `docs/game-design/interface/`

## Conflict Handling

- If old design docs conflict with current implementation, preserve the current
  implementation unless the user explicitly asks to redesign it.
- If old schema docs conflict with `src/shared/schemas`, treat `src/shared` as
  the active contract.
- If old UI notes conflict with current design system, preserve the current
  design system and adapt only the player-facing idea.
- Do not copy old folder architecture into `src/`.
- For world generation, navigation, exploration, and scenario exits, preserve
  the graph topology from `world/02_geography_and_topology.md`: square
  coordinates are an address space, while region exits are explicit gated graph
  transitions.

## Output Expectations

When using this skill, mention which design source files informed the change or
analysis. If the result is only planning or analysis, list candidate source
files and explain why each matters.

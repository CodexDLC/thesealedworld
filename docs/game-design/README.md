# Game Design Source

This directory stores design-source material migrated from the old
`Telegram_Bot_RPG` documentation. Treat these files as lore, RPG philosophy,
mechanic intent, naming rationale, and UX direction.

Do not treat this directory as current implementation architecture.

## Source Roots

- `domains/` - current design-source domains that have been reviewed or
  rewritten for this project.
- `designer/` - world, lore, combat, economy, RPG design, and scenario ideas.
- `rpg-rules/` - remaining older RPG rule sources that still need review.
- `rules/` - reviewed technical design references.
- `library/` - player-facing article sources that can later feed the in-game
  library.
- `drafts/` - exploratory notes that can inform future canon but need review before use.
- `interface/` - interface philosophy and old UI notes; use as UX intent only.

## Usage Rules

- Prefer these documents when deciding what a thing means in the game world:
  attribute names, skill fantasy, combat feel, progression philosophy, world tone,
  scenario intent, and player-facing terminology.
- Prefer current project code and schemas when deciding how a thing is stored,
  serialized, routed, validated, or rendered.
- When old schema documents conflict with current `src/shared` contracts or
  backend/frontend feature code, current code wins unless the task is explicitly
  to redesign the contract.
- When building UI, use these files for intent and current frontend CSS/templates
  plus `turnbasedmmorpg-design-system` for visual implementation rules.

## Most Useful Entry Points

- RPG attributes: `library/rpg/attributes.md`
- Attribute runtime reference: `rules/attributes/technical_reference.md`
- Items library source: `library/rpg/items.md`
- Items technical reference: `rules/items/item_model_reference.md`
- Weapon type source: `rules/items/weapon_type_source.md`
- Modifiers library source: `library/rpg/modifiers.md`
- Skills library source: `library/rpg/skills/README.md`
- Skill progression reference: `rules/skills/progression_reference.md`
- Skill catalog reference: `rules/skills/catalog_reference.md`
- Combat skill runtime reference: `rules/skills/combat_runtime_reference.md`
- Active combat actions: `rules/combat/active_actions.md`
- Gifts and magic schools: `rpg-rules/Gifts/README.md`
- Gifts and Symbiote concept: `domains/gifts/README.md`
- Modifier vocabulary: `rules/modifiers/modifier_vocabulary.md`
- Actor mapper reference: `rules/modifiers/actor_mapper_reference.md`
- World bible: `designer/world/00_world_bible.md`
- Combat vision: `designer/combat/README.md`
- RPG design overview: `designer/rpg/README.md`
- Scenario seed: `designer/scenarios/01_zero_shard.md`

# Game Design Source

This directory stores design-source material migrated from the old
`Telegram_Bot_RPG` documentation. Treat these files as lore, RPG philosophy,
mechanic intent, naming rationale, and UX direction.

Do not treat this directory as current implementation architecture.

## Source Roots

- `designer/` - world, lore, combat, economy, RPG design, and scenario ideas.
- `rpg-rules/` - attributes, skills, gifts, modifiers, item/weapon concepts, and old schema notes.
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
- When building UI, use these files for intent and `docs/design-system/` plus
  `turnbasedmmorpg-design-system` for visual implementation rules.

## Most Useful Entry Points

- RPG attributes: `rpg-rules/Attributes/README.md`
- Skill families: `rpg-rules/Skills/README.md`
- Skill balance philosophy: `rpg-rules/Skills/Core_Mechanics/Balance_Matrix.md`
- Skill progression concept: `rpg-rules/Skills/Core_Mechanics/Progression_Math.md`
- Gifts and magic schools: `rpg-rules/Gifts/README.md`
- Modifier vocabulary: `rpg-rules/Modifiers/Modifiers_Reference.md`
- World bible: `designer/world/00_world_bible.md`
- Combat vision: `designer/combat/README.md`
- RPG design overview: `designer/rpg/README.md`
- Scenario seed: `designer/scenarios/01_zero_shard.md`

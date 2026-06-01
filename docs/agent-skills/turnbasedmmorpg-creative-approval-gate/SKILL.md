---
name: turnbasedmmorpg-creative-approval-gate
description: Approval rules for creative, lore, balance, narrative, visual-direction, and content-catalog changes in TurnBasedMMORPG. Use before editing game-design content, lore text, UI art direction, public-facing copy, catalogs, balance numbers, rewards, monsters, items, skills, scenarios, or generated creative assets.
---

# TurnBasedMMORPG Creative Approval Gate

## Purpose

Reading, diagnosis, code navigation, and non-mutating analysis are allowed by default.

Routine implementation work may proceed when the user explicitly asks for code changes and the work does not alter creative intent, game design, lore, visual direction, balance, or player-facing content.

Before changing creative material, stop and ask for explicit user approval.

## Creative Material

Treat these as creative or product-content changes:

- lore, worldbuilding, scenario text, quest text, dialogue, news copy, and public-facing marketing copy
- game-design rules, progression formulas, rewards, economy values, combat tuning, monster behavior, item stats, skill definitions, and balance numbers
- visual direction, UI mood, illustration prompts, generated images, icons, palettes, typography direction, and gameplay presentation
- catalog resources under backend feature content folders when the edit changes player-visible meaning or balance
- generated assets or prompts that define product style, fiction, creatures, locations, or factions

## Allowed Without Extra Creative Approval

Proceed normally when the user has already explicitly requested the specific change and the edit is limited to:

- tests, type fixes, lint fixes, imports, or formatting
- bug fixes that preserve existing creative meaning and balance
- infrastructure, deployment, logging, diagnostics, or CI changes
- backend/frontend wiring that exposes existing approved content without changing it
- documentation that describes current behavior without inventing new lore, rules, or balance

## Required Approval Shape

When a requested implementation would modify creative material, report:

```text
This touches creative/game-design material:
- <files or surfaces>
- <what would change>
- <why it matters>

I can proceed after explicit approval.
```

Do not bury creative changes inside a broader code patch.

## Relationship To Codex Config

Global Codex `config.toml` controls technical permissions such as sandbox mode, shell approvals, and trusted project paths.

This skill controls semantic approval: when the agent should pause before changing project creative intent even if filesystem permissions allow the edit.

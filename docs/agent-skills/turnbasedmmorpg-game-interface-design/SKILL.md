---
name: turnbasedmmorpg-game-interface-design
description: Game interface design and prototype rules for TurnBasedMMORPG. Use when designing or editing gameplay UI, design_prototype pages, game HUDs, action panels, exploration/combat/scenario/loot/status/inventory screens, responsive game layouts, or reusable game UI components.
---

# TurnBasedMMORPG Game Interface Design

## First Reads

Read these before changing gameplay UI:

- `docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-design-system/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-game-css-shell/SKILL.md`

For combat UI, also read:

- `docs/agent-skills/turnbasedmmorpg-combat-contract/SKILL.md`

## Core Rule

Separate interface behavior from domain content.

Common behavior belongs in shared game components or shell/layout CSS. Domain CSS only decides what a specific screen puts inside those components.

Do not create a new domain-local panel, drawer, button language, footer, header, action bar, or shell container when the same behavior exists or should exist across gameplay screens.

## Layer Ownership

Use this order:

1. tokens: colors, fonts, spacing, borders, shadows, textures
2. shell: header, main, footer/chat, viewport, side-panel slots
3. layouts: mobile portrait, mobile landscape, tablet, desktop composition
4. components: action panel, buttons, drawers, cards, widgets, meters, tabs, lists
5. domain screen layer: exploration, combat, scenario, loot, status, inventory
6. prototype-only overrides

If a rule affects more than one gameplay domain, it is not domain CSS.

## CSS Naming Rule

Prefer a base class plus a domain modifier:

```css
.game-action-panel {}
.game-action-panel--bottom {}
.game-action-button {}
.game-action-drawer {}

.combat-action-panel {}
.exploration-action-panel {}
```

Avoid creating unrelated domain-only base systems for shared behavior:

```css
.combat-command-deck {}
.mobile-action-grid {}
.scenario-choice-panel {}
```

Those may exist only as domain wrappers or temporary prototype debt, not as the final reusable behavior layer.

## Action Panel Contract

Every gameplay screen that has player commands uses the shared action panel contract.

- The action panel position is common behavior.
- On mobile portrait, the action panel is pinned to the bottom of the main game area, above the chat drawer.
- The central screen/field takes remaining space above the action panel.
- The action panel must not consume half of mobile height unless the domain explicitly enters a dedicated command-selection mode.
- Drawers inside the action panel open as overlays and must not move the button that opened them.
- Clicking the same place should be able to close a drawer.
- Belt, abilities, local services, navigation, scenario choices, combat feints, loot actions, and encounter decisions are domain content inside the common action panel.
- Button surface, hover, disabled, active, icon mask, and metal/wood texture behavior are shared component concerns.

## Prototype Rules

For `design_prototype/`:

- Do not put all states into one giant HTML file.
- Create purpose pages such as `exploration.html`, `combat.html`, `status.html`, `inventory.html`, `scenario.html`, and `loot.html`.
- Each purpose page may show mobile, mobile landscape, tablet, and desktop frames side by side.
- Keep shared prototype imports in entry CSS and reusable components.
- Keep domain-specific layout in `design_prototype/css/screens/<domain>.css`.
- When a pattern appears in two domains, stop and move the base behavior into `design_prototype/css/components/` before extending it further.
- Prototype CSS should mirror the future production split: tokens, shell, layouts, components, screen layer.

## Game Screen Structure

Gameplay screens should be assembled from stable slots:

- header/menu slot
- main viewport/field slot
- left side panel slot
- right side panel slot
- bottom action panel slot
- footer chat drawer slot

Domain screens decide content:

- exploration: scene text/art, local services, navigation grid, encounter interrupt
- combat: actor state, exchange text, belt, abilities, feints, attack/refresh
- scenario: narrative, choices, requirements, result state
- loot: corpse/item list, inspect, claim, split, discard
- status: avatar, resources, attributes, skills, build actions
- inventory: containers, equipped gear, belt/pockets, item details

The slots themselves are shared.

## Mobile Priority

Mobile portrait is the hardest layout and must be designed first.

- Keep the main game field readable.
- Avoid turning actor/resource/status areas into scroll zones unless the screen is explicitly a panel or inventory.
- Chat expands upward and may cover lower UI by design.
- Drawers must not reflow critical controls.
- Text controls that require reading get height priority over icon-only controls.
- Icon-only ability/belt/tool rows must stay compact.

## Desktop And Tablet

Tablet and desktop reuse the same component contracts with different layout placement.

- Side panels may become persistent on desktop but drawer-based on mobile/tablet.
- Wider screens should add useful spacing or side panels, not stretch every button into oversized strips.
- Desktop game menu can be full navigation; mobile can use burger/menu behavior.
- Do not solve desktop by copying mobile widths blindly, and do not solve mobile by shrinking desktop.

## Data Honesty

Do not invent gameplay data just to fill a design.

- Use real catalog/view-model fields when available.
- Use explicit empty, unknown, locked, or `NO_DATA` states when data is not available.
- Do not show database keys as player coordinates or labels.
- Convert internal ids into player-facing names, coordinates, or unknown states.

## Required Self-Check

Before finishing gameplay UI work, report:

- Which shared component/shell class owns the behavior.
- Which domain class only customizes content.
- Whether any page-local CSS should be promoted to a component.
- Whether the mobile action panel leaves enough room for the main game field.

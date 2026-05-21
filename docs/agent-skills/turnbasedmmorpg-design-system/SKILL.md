---
name: turnbasedmmorpg-design-system
description: Design-system guidance for TurnBasedMMORPG frontend work. Use when creating or editing frontend UI, Jinja templates, HTMX fragments, Alpine interactions, shared CSS, shell includes, game-menu markup, or domain UI, especially when Codex must reuse existing project classes before introducing new styles.
---

# TurnBasedMMORPG Design System

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-design-system/references/design-system-rules.md`

Then open, only as needed:

- current CSS under `src/frontend/static/css/`
- current templates under `src/frontend/templates/`
- archived reference under `docs/archive/design-system/` only for historical context

If the task changes frontend structure broadly, also use `turnbasedmmorpg-frontend`.

If the task changes game shell CSS, responsive layout, side panels, header/footer, game menu, chat/HUD placement, or domain viewport sizing, also use `turnbasedmmorpg-game-css-shell`.

If the task is UI design work, also use exactly the relevant surface skill:

- `turnbasedmmorpg-site-design` for public site and account pages.
- `turnbasedmmorpg-cabinet-design` for cabinet/admin/operational pages.
- `turnbasedmmorpg-game-interface-design` for gameplay HUDs, `design_prototype`, and game domain screens.

## Core Rules

- Treat the current code in `src/frontend/static/css/` and `src/frontend/templates/` as the active UI contract.
- Treat `docs/archive/design-system/` as historical reference only, not as canon.
- Do not treat `/system/design` as canonical.
- Reuse existing shared classes before introducing new CSS.
- Extend shared components before adding page-local styles.
- Inspect shared shell templates and their CSS together before editing header, footer, or navigation.
- Keep tokens, shell/layout, components, and domain screen CSS separate. Do not hide reusable component behavior inside a domain CSS file.

## Reuse Order

Use this order:

1. `src/frontend/static/css/core/tokens.css`
2. `src/frontend/static/css/components/*.css`
3. `src/frontend/static/css/includes/*.css`
4. shared game shell templates under `src/frontend/templates/game/includes/`
5. domain templates under `src/frontend/templates/game/domains/`
6. page CSS
7. inline styles only for dynamic values or diagnostics

## Surface Split

The project has three UI design surfaces:

- Site design: public and account-facing pages.
- Cabinet design: admin and operational interfaces.
- Game interface design: gameplay HUDs and game prototypes.

Do not transfer patterns between these surfaces without an explicit reason. A public-site hero, a cabinet dashboard panel, and a gameplay action panel are different design systems sharing only low-level tokens and primitives.

## Component Promotion Rule

When the same behavior appears in two domains, promote it to a shared component before extending it further.

Examples:

- action panel positioning
- drawer overlay behavior
- button surface and icon masks
- side panel shell
- chat drawer shell
- status/resource meters

Domain CSS may provide content and small variants; it must not own shared behavior.

## Shared Drift Check

Before changing header, footer, or navigation, inspect both sides of the contract:

- template
- shared CSS
- archived design-system reference only if historical intent is useful

Current known drift lives in:

- `src/frontend/static/css/includes/header.css`
- `src/frontend/static/css/includes/footer.css`
- `src/frontend/static/css/components/navigation.css`

Do not patch around these with page-level CSS if the task is really a shared-shell issue.

## Typical Actions

- Find the closest existing class and reuse it
- Move reusable patterns into shared components when page CSS started duplicating them
- Keep game shell decisions in `game/base_game.html`, `game/session.html`, `game/includes/*`, and `game/domains/*`
- Keep status-like reusable UI in components, not in a gameplay domain unless it is truly domain-specific

## Validation

When the task changes shared UI:

- verify class reuse against the current CSS/templates
- verify no new shared class was added where an existing class already fit
- verify shared template class names still match the shared CSS that claims to style them

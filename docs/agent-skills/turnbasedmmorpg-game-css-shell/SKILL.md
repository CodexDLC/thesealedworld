---
name: turnbasedmmorpg-game-css-shell
description: Game CSS shell and responsive layout rules for TurnBasedMMORPG. Use when changing game UI CSS, compiled CSS sources, base_game/session shell templates, side panels, header/footer, game menu, drawer behavior, chat/HUD windows, or scenario/exploration/arena/combat/status layouts.
---

# TurnBasedMMORPG Game CSS Shell

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-game-css-shell/references/responsive-shell.md`
- `GAME_LAYOUT_RESPONSIVE_PLAN.md`

Also use:

- `turnbasedmmorpg-frontend` for frontend routing/template/API boundaries.
- `turnbasedmmorpg-design-system` for visual/component reuse.
- `turnbasedmmorpg-game-interface-design` for gameplay HUD composition, action panels, prototype pages, and domain screen design.

## Core Rules

- Treat `src/frontend/static/css/game.css` as compiled output. Do not edit it directly.
- Treat `src/frontend/static/css/game_bundle.css` as the game CSS source entry.
- Treat `src/frontend/static/css/pages/game/layout.css` as the base desktop-first shell model.
- Treat `src/frontend/static/css/pages/game/layout_responsive.css` as the shared responsive and drawer contract.
- Keep shell behavior in shell CSS. Domain CSS should style content inside shell containers.
- If side panel behavior or breakpoint behavior is wrong across screens, fix `layout_responsive.css`, not every domain CSS file.
- If one feature's content overflows, fix that feature's internal CSS using shell tokens.
- Before editing shared shell selectors, inspect all current definitions with `rg`.
- Gameplay action panel placement, chat slot behavior, side panel slots, and viewport sizing are shell/component contracts. Do not reimplement them independently in exploration, combat, scenario, loot, or inventory CSS.

## Shell-Owned Selectors

Do not redefine these in domain CSS unless the task is explicitly shell refactor work:

- `.game-header`
- `.game-footer`
- `.center-nav`
- `.cnav-btn`
- `.game-menu-icon`
- `.game-top-row`
- `.col-left`
- `.col-center`
- `.col-center-inner`
- `.col-right`
- `.shell-constrained`
- `#game-chat-shell`
- `.hud-window`

## Verification

For shell/responsive work:

- Run `git diff --check`.
- Do not hand-edit compiled `game.css`.
- Compile static output only when integration is ready.
- Check viewports: `1600`, `1440`, `1280`, `1024`, `768`, `500`.
- Search for accidental shell selector duplication in domain CSS.

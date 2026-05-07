# Responsive Game Shell Reference

## CSS Source Layers

Use these layers in order:

1. `src/frontend/static/css/core/tokens.css`: global design tokens.
2. `src/frontend/static/css/components/*.css`: shared components.
3. `src/frontend/static/css/pages/game/layout.css`: base game shell.
4. `src/frontend/static/css/pages/game/*`: domain/content CSS modules.
5. `src/frontend/static/css/pages/game/layout_responsive.css`: shared responsive shell overrides.
6. `src/frontend/static/css/game_bundle.css`: source entry that imports game modules.
7. `src/frontend/static/css/game.css`: compiled output, never direct-edit.

`layout_responsive.css` is imported last so it can protect the shared shell from older domain-level duplication.

## Base Shell Files

Templates:

- `src/frontend/templates/game/base_game.html`
- `src/frontend/templates/game/session_content.html`
- `src/frontend/templates/game/session_content_inner.html`
- `src/frontend/templates/game/includes/header.html`
- `src/frontend/templates/game/includes/footer.html`
- `src/frontend/templates/game/domains/game_menu/header_nav.html`

CSS:

- `src/frontend/static/css/pages/game/layout.css`
- `src/frontend/static/css/pages/game/layout_responsive.css`

JS:

- `src/frontend/static/js/core/game_shell.js`

## Shell Tokens

Use these tokens instead of hard-coding shell dimensions in feature CSS:

- `--side-panel-width`
- `--side-panel-width-compact`
- `--game-drawer-width`
- `--center-content-max`
- `--game-header-height`
- `--game-footer-height`
- `--game-ui-scale`
- `--game-panel-z`
- `--game-overlay-z`

Feature CSS may introduce feature-local tokens, such as `--scenario-avatar-width`, but should derive them from viewport or shell context rather than redefining shell columns.

## Breakpoint Contract

Shared shell behavior:

- `>=1600`: full desktop shell.
- `1440-1599`: compact desktop width tuning.
- `1280-1439`: right panel becomes overlay drawer.
- `1025-1279`: side panels become narrower, center is protected.
- `769-1024`: both panels use drawer mechanics.
- `<=768`: mobile shell; both side panels are fixed overlay drawers.
- `<=500`: narrow phone drawer and compact shell text.

If these thresholds feel wrong globally, change `layout_responsive.css`. If only one screen feels wrong, change that screen's internals.

## Domain CSS Responsibilities

Domain CSS may own:

- inner content grids;
- cards, action lists, text blocks, story panels;
- local avatar/image sizing;
- local scroll containers;
- feature-specific empty states;
- feature-specific breakpoints for content only.

Domain CSS must not own:

- shell column behavior;
- drawer mechanics;
- header/footer structure;
- game menu base layout;
- `leftOpen/rightOpen` grid behavior;
- global chat/HUD z-index layering.

## Common Workflow

1. Read `GAME_LAYOUT_RESPONSIVE_PLAN.md`.
2. Identify whether the issue is shell behavior or feature content behavior.
3. For shell behavior, edit `layout.css` or `layout_responsive.css`.
4. For feature content, edit only that feature CSS/template.
5. Avoid editing `game.css`; compile it later from `game_bundle.css`.
6. Verify with `git diff --check` and viewport checks.

## Search Commands

Find shell selector duplication:

```powershell
rg "\.game-header|\.game-footer|\.center-nav|\.cnav-btn|\.game-menu-icon|\.game-top-row|\.col-left|\.col-center|\.col-right" src\frontend\static\css\pages\game
```

Find breakpoints:

```powershell
rg "@media" src\frontend\static\css\pages\game src\frontend\static\css\components src\frontend\static\css\layout
```

Find compiled/source entry references:

```powershell
rg "game_bundle|game.css|layout_responsive" src\frontend\static\css src\frontend\templates docs tests
```

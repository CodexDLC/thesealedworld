# Design System Rules

## First Reads

Read:

- `docs/design-system/README.md`
- `docs/design-system/Design System.html`

Use the README as the text source of truth and the HTML file as the visual source of truth.

## Priority Order

Apply this order when building UI:

1. `src/frontend/static/css/core/tokens.css`
2. `src/frontend/static/css/components/*.css`
3. `src/frontend/static/css/includes/*.css`
4. `src/frontend/templates/game/includes/*`
5. `src/frontend/templates/game/domains/*`
6. page-level CSS
7. inline styles

## Do Not

- Do not add new button classes before checking `components/buttons.css`
- Do not add new panel classes before checking `components/panels.css`
- Do not add new navigation markup or classes before checking `game/domains/game_menu/header_nav.html`
- Do not treat broken shared CSS as permission to write page-local replacements
- Do not use `/system/design` as the design reference
- Do not reference `tools/icon-reserve/` assets directly from templates, JSON, or browser code

## Reuse Targets

Prefer these shared classes first:

- `btn-node`
- `panel-membrane`
- `ds-panel`
- `stat-*`
- `world-text`
- `whisper`
- `choice`

## Known Shared-Layer Drift

These files should be treated carefully because they do not fully match the active templates:

- `src/frontend/static/css/includes/header.css`
- `src/frontend/static/css/includes/footer.css`
- `src/frontend/static/css/components/navigation.css`

If a task touches header, footer, or game menu, inspect both the CSS file and the template file before editing.

## Combat UI Notes

Combat may need a stricter game-menu/header mode than exploration or scenario. It is acceptable for combat UI to close, disable, or replace header tabs/windows when the battle screen needs focus, but the behavior must be handled in the game session/menu layer and remain domain-aware.

Combat templates should be designed around separate surfaces: center battlefield/viewport, actor cards, action controls, target state, effect/feint badges, side panels, and combat log feed. Use explicit empty or `NO_DATA` states when backend data is not available yet.

For icons, use semantic keys from backend/catalog/view models and map them to frontend-owned SVG files under `src/frontend/static/images/ui/`. Missing combat icons should be copied and adapted from `tools/icon-reserve/game-icons-net/` into a frontend-owned folder before use.

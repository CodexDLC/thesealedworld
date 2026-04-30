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

# Design System Rules

## First Reads

Read:

- current CSS under `src/frontend/static/css/`
- current templates under `src/frontend/templates/`
- archived reference under `docs/archive/design-system/` only if historical intent is useful

Use the current CSS/templates as the source of truth. The archived design-system
folder is not canonical.

## Priority Order

Apply this order when building UI:

1. `src/frontend/static/css/core/tokens.css`
2. `src/frontend/static/css/components/*.css`
3. `src/frontend/static/css/includes/*.css`
4. `src/frontend/templates/game/includes/*`
5. `src/frontend/templates/game/domains/*`
6. page-level CSS
7. inline styles

## Surface-Specific Skills

Before UI design work, use the matching surface skill:

- `turnbasedmmorpg-site-design` for public website and account pages.
- `turnbasedmmorpg-cabinet-design` for cabinet/admin/operational pages.
- `turnbasedmmorpg-game-interface-design` for gameplay HUDs, game prototypes, and domain screens.

The general frontend skill describes service architecture. It does not replace surface-specific design rules.

## Do Not

- Do not add new button classes before checking `components/buttons.css`
- Do not add new panel classes before checking `components/panels.css`
- Do not add new navigation markup or classes before checking `game/domains/game_menu/header_nav.html`
- Do not treat broken shared CSS as permission to write page-local replacements
- Do not use `/system/design` as the design reference
- Do not reference `tools/icon-reserve/` assets directly from templates, JSON, or browser code
- Do not put shared layout behavior into a domain screen CSS file just because the first implementation happens inside one domain
- Do not create separate action panel, drawer, or button systems for exploration, combat, scenario, and loot

## Reuse Targets

Prefer these shared classes first:

- `btn-node`
- `panel-membrane`
- `ds-panel`
- `stat-*`
- `world-text`
- `whisper`
- `choice`

## Component Promotion Rule

If two domains need the same behavior, the base behavior belongs in a component.

Domain files may contain:

- domain content layout
- domain-specific labels/icons/state colors
- small responsive overrides

Domain files must not own:

- shell placement
- common action panel position
- common drawer overlay behavior
- common button surface
- common side panel mechanics
- common chat drawer mechanics

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

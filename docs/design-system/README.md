# TurnBasedMMORPG Design System

## Canonical Sources

Use these files in this order:

1. `docs/design-system/Design System.html`
2. `docs/design-system/README.md`
3. CSS source files under `src/frontend/static/css/core/`, `components/`, and `includes/`

Treat `docs/design-system/Design System.html` as the visual canon. It is a standalone reference and does not depend on frontend routes, `site/base_site.html`, or runtime CSS bundles.

Do not treat `http://localhost:8000/system/design` as canonical. That runtime page is only a preview surface and has already drifted from the standalone reference.

## Usage Order

When building or changing frontend UI, use this priority order:

1. Reuse existing design-system tokens from `src/frontend/static/css/core/tokens.css`
2. Reuse existing shared component classes from `src/frontend/static/css/components/`
3. Reuse existing include-level shell classes from `src/frontend/static/css/includes/`
4. Extend an existing shared component if the pattern is close but incomplete
5. Add domain-specific styles only when the pattern is truly domain-specific
6. Add page-level styles only for unique page composition
7. Use inline styles only for dynamic values or temporary diagnostics

Do not create new button, panel, tag, stat, or navigation classes before checking whether an existing shared class already covers the need.

## Core Style Map

Primary token source:

- `src/frontend/static/css/core/tokens.css`

Primary shared components:

- `src/frontend/static/css/components/buttons.css`
- `src/frontend/static/css/components/panels.css`
- `src/frontend/static/css/components/stats.css`
- `src/frontend/static/css/components/inventory.css`
- `src/frontend/static/css/components/chat.css`
- `src/frontend/static/css/components/navigation.css`
- `src/frontend/static/css/components/cards.css`
- `src/frontend/static/css/components/misc.css`

Shell and include styles:

- `src/frontend/static/css/includes/header.css`
- `src/frontend/static/css/includes/footer.css`
- `src/frontend/static/css/includes/navigation.css`

Game shell templates:

- `src/frontend/templates/game/base_game.html`
- `src/frontend/templates/game/session.html`
- `src/frontend/templates/game/includes/header.html`
- `src/frontend/templates/game/includes/footer.html`
- `src/frontend/templates/game/domains/game_menu/header_nav.html`

## External Icon Packs

Scenario choice icons may use selected SVG assets from Game-icons.net, especially for skill, warning, action, and item glyphs. Store any adopted assets locally under `src/frontend/static/images/ui/` and keep scenario data semantic, for example `icon: "warning"` or `icon: "strength"`, instead of embedding filenames or visual text in scenario JSON.

Game-icons.net assets are licensed under CC BY 3.0 or, for some assets, Public Domain. When using them, record the original icon name, author, source URL, and license in an attribution file near the copied assets. Before public release, expose those credits on a public `Credits` / `Lizenzen` page linked from the footer, separate from `Datenschutz`.

## Audit Summary

This audit checks core pieces and shared shell pieces, not page-specific screens.

### Aligned With Design System

- `src/frontend/static/css/core/tokens.css`
  The project keeps the same token families as the standalone design system: colors, semantic text tokens, spacing, typography, clip-path nodes, rarity tokens, and chat semantic tokens.

- `src/frontend/static/css/components/buttons.css`
  `btn-node`, size variants, `danger`, `ghost`, and `psi` stay aligned with the standalone design language.

- `src/frontend/static/css/components/panels.css`
  `panel-membrane`, `ds-panel`, `world-text`, `whisper`, and `choice` still reflect the reference design language closely.

### Confirmed Drift

- `src/frontend/static/css/includes/header.css`
  This stylesheet still targets `.header-logo`, `.logo-text`, and `.header-status`, but the live template `src/frontend/templates/game/includes/header.html` now uses `.header-left`, `.game-logo`, `.header-center`, `.header-right`, `.server-status`, and `.connection-stats`. The file is no longer the true source of the current header structure.

- `src/frontend/static/css/components/navigation.css`
  This file still models prototype navigation classes like `.nb`, `.bnt`, and `.bn-div`, but the live game menu template `src/frontend/templates/game/domains/game_menu/header_nav.html` now uses `.center-nav`, `.cnav-btn`, and `.cnav-spacer`. Shared navigation CSS is no longer matched to the active game-menu markup.

- `src/frontend/static/css/includes/footer.css`
  The file still carries older site-shell assumptions like `.app-footer` and `.footer-container`. It partially styles `.game-footer`, but the current game footer template `src/frontend/templates/game/includes/footer.html` has a narrower structure and should be treated as the active markup contract.

## Agent Rules

When an agent changes frontend UI in this repository:

- Open `docs/design-system/README.md` first
- Use existing classes before inventing new ones
- Check shared CSS before page CSS
- Treat class drift in shared shell files as a maintenance issue, not a reason to create more one-off styles
- If a shared pattern is missing, extend the shared layer instead of patching a page directly

## Current Warning

The runtime page `/system/design` is currently not a reliable truth source because:

- it renders inside `site/base_site.html`
- it inherits site shell chrome
- its active runtime bundle does not include the original `pages/design_system.css` path

Use the standalone HTML file in this folder instead.

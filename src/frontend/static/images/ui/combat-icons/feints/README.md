# Feint Icons

Per-feint SVG icons rendered on combat action buttons.

## Lookup order

The frontend view model resolves a feint icon URL in this order:

1. **Per-feint icon** — `<feint_id>.svg` if the file name appears in
   `FEINT_SPECIFIC_ICON_FILES` (`src/frontend/game_features/combat/view_models/screen.py`).
2. **Group fallback** — `group-<purchase_group>.svg` for `basic`, `tactical`, `weapon`.
3. **Last fallback** — the generic `combat-icons/feint.svg`.

## Adding a unique icon for a feint

1. Pick a 512×512 single-path SVG (white fill on transparent) from
   `tools/icon-reserve/game-icons-net/` (gitignored — use `browser.html` locally).
2. Copy it here as `<feint_id>.svg` (e.g. `measured_strike.svg`).
3. Add `feint_id` to `FEINT_SPECIFIC_ICON_FILES` in
   `src/frontend/game_features/combat/view_models/screen.py`.

Sub-categories that share a shape but differ in color can keep the same
SVG path and recolor via CSS filter.

## Starter set

`group-basic.svg`, `group-tactical.svg`, `group-weapon.svg` are minimal
placeholders so all feints have a recognisable group glyph until unique
icons are sourced.

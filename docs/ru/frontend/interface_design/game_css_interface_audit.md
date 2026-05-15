# Аудит CSS игрового интерфейса

Дата: 2026-05-13

Цель: понять, какие реальные CSS/шаблонные слои уже существуют, какие prototype-компоненты им соответствуют, что надо переиспользовать, а что переписать перед переносом `design_prototype` в Jinja/templates.

## Проверенные источники

Production CSS:

- `src/frontend/static/css/game_bundle.css`
- `src/frontend/static/css/compiler_config.json`
- `src/frontend/static/css/core/tokens.css`
- `src/frontend/static/css/components/common/buttons.css`
- `src/frontend/static/css/components/common/panels.css`
- `src/frontend/static/css/components/game/chat.css`
- `src/frontend/static/css/components/game/cards.css`
- `src/frontend/static/css/components/game/stats.css`
- `src/frontend/static/css/pages/game/layout.css`
- `src/frontend/static/css/pages/game/layout_responsive.css`
- `src/frontend/static/css/pages/game/viewport.css`
- `src/frontend/static/css/pages/game/chat.css`
- `src/frontend/static/css/pages/game/combat.css`
- `src/frontend/static/css/pages/game/scenario.css`
- `src/frontend/static/css/pages/game/status.css`

Production templates:

- `src/frontend/templates/game/base_game.html`
- `src/frontend/templates/game/session_content.html`
- `src/frontend/templates/game/session_content_inner.html`
- `src/frontend/templates/game/includes/header.html`
- `src/frontend/templates/game/includes/footer.html`
- `src/frontend/templates/game/domains/game_menu/header_nav.html`
- `src/frontend/templates/game/domains/exploration/viewport/main.html`
- `src/frontend/templates/game/domains/combat/viewport/main.html`
- `src/frontend/templates/game/domains/scenario/viewport/main.html`
- `src/frontend/templates/game/components/panel/main.html`
- `src/frontend/templates/game/components/status/main.html`

Prototype CSS:

- `design_prototype/css/prototype_imports.css`
- `design_prototype/css/components/game-shell.css`
- `design_prototype/css/components/action-panel.css`
- `design_prototype/css/components/mobile-screen.css`
- `design_prototype/css/components/mobile-chat.css`
- `design_prototype/css/components/panel-dock.css`
- `design_prototype/css/screens/exploration.css`
- `design_prototype/css/screens/combat-prototype.css`

## Production entry state

`game_bundle.css` is the real source entry for game CSS. `game.css` is compiled output and must not be edited directly.

Current production order:

1. core tokens/reset/animations
2. common components
3. game components
4. game shell/pages
5. domain CSS
6. responsive shell

Current compiler mapping:

```json
"game_bundle.css": "game.css"
```

Decision: new real shared gameplay components must be imported from `game_bundle.css`, not patched into compiled `game.css`.

## Real Shell Inventory

Production already has a real game shell. The important classes/ids are:

- `#app-viewport`
- `.game-container`
- `.shell-constrained`
- `.game-header`
- `#main-content`
- `.game-top-row`
- `.col-left`
- `.col-center`
- `.col-center-inner`
- `.col-right`
- `#center-screens`
- `.cs`
- `.game-footer`
- `#game-chat-shell`
- `.game-chat-row`

Ownership:

- `layout.css` owns the base desktop shell.
- `layout_responsive.css` owns responsive breakpoints, side-panel drawer behavior, header/footer heights, and center width variables.
- `base_game.html`, `session_content.html`, and `session_content_inner.html` own the Jinja shell structure.

Decision:

- Do not replace production shell with prototype `game-shell`.
- Prototype `game-shell` is a naming/contract draft.
- Production should evolve existing shell classes instead of introducing a parallel shell.
- If neutral naming is wanted later, add aliases carefully, but keep existing shell behavior stable first.

## Header And Footer/Chat

Production header:

- `game-header`
- `header-left`
- `header-center`
- `header-right`
- `center-nav`
- `cnav-btn`
- `game-menu-icon`

Production footer:

- `game-footer` currently renders technical status.
- `#game-chat-shell` is the real expandable chat overlay.
- Chat is not just a footer. The practical game footer is the collapsed/expanded chat mechanism plus the small technical footer.

Production chat:

- `#game-chat-shell`
- `.game-chat-launcher`
- `.game-chat-row`
- `.chat-panel`
- `.chat-tabs`
- `.chat-tab-group`
- `.chat-win-controls`
- `.chat-main-area`
- `.chat-log`
- `.chat-users`
- `.chat-input-row`
- responsive rules in `pages/game/chat.css`.

Prototype:

- `mobile-rift-footer`
- `mobile-chat-drawer`
- `mobile-chat-summary`
- `mobile-chat-panel`

Decision:

- Do not port prototype `mobile-chat-*` directly into production.
- The production chat mechanism already exists and is better developed.
- Prototype should visually model the compact chat header, but production should reuse `#game-chat-shell` and `.game-chat-row`.
- Need a mobile/collapsed chat header variant in production chat CSS, not a separate footer component.

## Center Screen / Main Container

Production center:

- `#center-screens`
- `.cs`
- `.cs.active`
- `.col-center`
- `.col-center-inner`

Current issue:

- `#center-screens` and `.cs` live in `pages/game/viewport.css`, but they are not only exploration viewport behavior. They are the shared center-screen contract.
- `.dp` also lives in `viewport.css`, although it acts like a reusable game action button.

Prototype:

- `game-main`
- `game-screen-area`
- `game-screen-area--vertical`
- `game-screen-content`
- `game-screen-footer`

Decision:

- Production should keep existing `#center-screens` / `.cs` for now.
- Move the generic center-screen contract out of `pages/game/viewport.css` into a shared game component or shell file when refactoring.
- Suggested target: `src/frontend/static/css/components/game/screen.css` or a split `pages/game/shell.css` if we keep it shell-owned.
- Domain CSS should not own center-screen positioning.

## Action Panel Inventory

Production has action panel behavior, but it is split incorrectly:

Exploration:

- `.exploration-control-panel`
- `.exploration-control-grid`
- `.exploration-action-block`
- `.exploration-route-block`
- `.exploration-movement-block`
- `.exploration-movement-grid`
- `.exploration-encounter-actions`
- `.dp`

Combat:

- `.combat-command-deck`
- `.combat-command-head`
- `.combat-action-topline`
- `.combat-primary-action`
- `.combat-action-group`
- `.combat-action-list`
- `.combat-feint-row`
- `.combat-feint-option`
- `.combat-ability-grid`
- `.combat-ability-option`
- `.combat-belt-grid`
- `.combat-belt-slot`

Shared-ish but misplaced:

- `.dp` is a real reusable action button surface, but it lives in `pages/game/viewport.css`.
- `combat-primary-action`, `combat-feint-option`, `combat-ability-option`, `combat-belt-slot` duplicate button surface logic instead of extending one shared action button.

Prototype:

- `game-action-panel`
- `game-action-panel--bottom`
- `game-action-panel__head`
- `game-action-panel__body`
- `game-action-panel__tools`
- `game-action-panel__decisions`
- `game-action-button`
- `game-action-button--icon`
- `game-action-button--primary`
- `game-action-button--empty`
- `game-action-drawer`
- `game-action-drawer__content`

Decision:

- Production needs a real shared action component.
- Suggested target: `src/frontend/static/css/components/game/action_panel.css`.
- Import it in `game_bundle.css` before domain page CSS.
- `action_panel.css` should absorb the generic parts of `.dp`, `.combat-primary-action`, `.combat-feint-option`, `.combat-ability-option`, and prototype `game-action-*`.
- Domain CSS should keep only domain-specific layout and state:
  - exploration navigation grid/movement/service grouping;
  - combat feint list, token strip, ability/belt content layout;
  - scenario choice content;
  - loot actions.

## Button Surface

Existing button layers:

- `btn-node` in `components/common/buttons.css` is a generic site/common node button.
- `.dp` in `pages/game/viewport.css` is the real game action button surface.
- `combat-primary-action`, `combat-feint-option`, `combat-ability-option`, and `combat-belt-slot` duplicate game button texture/border/hover.

Decision:

- Do not use `btn-node` as the main gameplay action button. It is too generic and shared across site/cabinet contexts.
- Promote `.dp` behavior into a game-specific shared action button:
  - proposed class: `.game-action-button`
  - variants: `--primary`, `--icon`, `--danger`, `--empty`, `--disabled`
- Existing `.dp` can remain as a compatibility alias during migration.

Compatibility approach:

```css
.game-action-button,
.dp {
  /* shared game action surface */
}
```

Then gradually update templates from `.dp` to `.game-action-button`.

## Panels And Sidebars

Existing shared panel:

- `ds-panel`
- `ds-panel-header`
- `ds-panel-body`
- `panel-membrane`
- `panel-refresh-button`

Existing shell side panels:

- `.col-left`
- `.col-right`
- responsive drawer behavior in `layout_responsive.css`

Prototype:

- `panel-dock`
- `side-panel-drawer`
- `status-widget-*`
- `info-widget-*`

Decision:

- Production side-panel mechanics already exist through `.col-left` / `.col-right`.
- Do not port prototype `side-panel-drawer` as a separate production drawer system.
- Prototype `status-widget-*` and `info-widget-*` should be compared with production `game/components/panel/widgets/*` before moving.
- Production should probably grow shared panel widget CSS rather than duplicate status/info widgets per domain.

## Combat Real State

Production combat is already more advanced than the prototype in several areas:

- `combat_screen.token_bar` already renders token `icon_url` and value.
- feints already have pin behavior and catalog/tooltips.
- abilities already use icon URLs.
- belt slot styles exist in CSS, though current viewport template does not expose the belt as a mobile action drawer.
- combat result screen exists.
- right/left combat sidebars exist.

Problems:

- `.combat-command-deck` owns both panel shell and combat content.
- action controls are not using a shared game action panel contract.
- mobile portrait layout is not designed enough around bottom action panel and main field priority.

Decision:

- Do not copy prototype combat data labels into production.
- Use production combat view model fields.
- Use prototype only for layout decisions:
  - bottom action panel;
  - belt/abilities as compact drawers;
  - feints and primary actions as main command content;
  - main combat field priority on mobile.

## Exploration Real State

Production exploration already has:

- scene/art/text via `.parchment`, `.scene-img`, `.world-text`
- location HUD strip
- service cards
- movement cooldown
- movement grid
- encounter panel with roster/detail/actions

Problems:

- action panel behavior is embedded in `.exploration-control-panel`.
- `.dp` is reusable but lives under viewport CSS.
- old clip-path/skew decisions still exist in real CSS, while the current prototype wants straight frames/buttons.
- production still shows `loc_id` style internal identifiers in places and needs player-facing coordinates/names.

Decision:

- Reuse production data flow and templates.
- Refactor action controls to shared `game-action-panel`.
- Keep exploration-specific layout in `pages/game/exploration.css` or split from current `viewport.css`.
- Move `.dp` into the new shared game action component.

## Proposed Production CSS Split

Near-term target:

```text
src/frontend/static/css/components/game/screen.css
src/frontend/static/css/components/game/action_panel.css
src/frontend/static/css/components/game/action_buttons.css
src/frontend/static/css/components/game/drawers.css
src/frontend/static/css/components/game/chat.css
src/frontend/static/css/components/game/panel_widgets.css

src/frontend/static/css/pages/game/layout.css
src/frontend/static/css/pages/game/layout_responsive.css
src/frontend/static/css/pages/game/viewport.css
src/frontend/static/css/pages/game/exploration.css
src/frontend/static/css/pages/game/combat.css
src/frontend/static/css/pages/game/scenario.css
src/frontend/static/css/pages/game/status.css
```

Important:

- `layout.css` / `layout_responsive.css` own shell and side panel mechanics.
- `components/game/screen.css` owns center screen/viewport reusable classes.
- `components/game/action_panel.css` owns bottom action panel and drawer behavior.
- Domain CSS only arranges domain content inside shared components.

## Prototype To Production Mapping

| Prototype class | Production status | Decision |
| --- | --- | --- |
| `game-shell` | Existing shell is `game-container`, `shell-constrained`, `game-top-row` | Do not port directly; use as naming reference only |
| `game-shell__header` | Existing `game-header` | Keep production class |
| `game-shell__main` / `game-main` | Existing `#main-content`, `.game-top-row`, `.col-center` | Keep production shell |
| `game-shell__footer` | Existing `game-footer` plus `#game-chat-shell` | Chat remains overlay, footer stays technical/compact |
| `game-screen-area` | Existing `#center-screens` / `.cs` | Move generic screen contract to shared component later |
| `game-action-panel` | No real shared equivalent | Create production component |
| `game-action-panel--bottom` | No real shared equivalent | Create production component |
| `game-action-button` | Similar to `.dp`, combat buttons duplicate it | Promote `.dp`/combat surfaces into shared component |
| `game-action-drawer` | No shared action drawer | Create production component |
| `mobile-chat-drawer` | Production chat already exists | Do not port; add compact chat header variant to production chat |
| `panel-dock` | Production side panels use `.col-left/.col-right` and `ds-panel` | Do not port as shell; reuse ideas for panel widgets only |

## Migration Plan

### Phase 1: Shared CSS extraction

1. Add `src/frontend/static/css/components/game/action_panel.css`.
2. Add it to `game_bundle.css` before `pages/game/viewport.css` and `pages/game/combat.css`.
3. Move common button surface from `.dp` into `.game-action-button`.
4. Keep `.dp` as compatibility alias.
5. Move common bottom panel/drawer behavior from prototype into production `action_panel.css`.

### Phase 2: Exploration template alignment

1. Wrap exploration controls with `.game-action-panel game-action-panel--bottom exploration-action-panel`.
2. Convert movement/service/encounter buttons to `.game-action-button`.
3. Keep `exploration-*` classes for navigation/service/encounter content only.
4. Remove shared action behavior from `viewport.css` once aliases are stable.

### Phase 3: Combat template alignment

1. Wrap combat commands with `.game-action-panel game-action-panel--bottom combat-action-panel`.
2. Convert primary/feint/ability/belt controls to shared action button variants.
3. Implement belt/abilities as action drawers for mobile.
4. Keep combat-specific token, actor, exchange, feint, and target layout in `combat.css`.

### Phase 4: Chat/footer alignment

1. Treat `#game-chat-shell` as the real footer-like interactive layer.
2. Add compact/mobile chat header mode using existing `.chat-tabs`, `.chat-win-controls`, `.chat-mini-*`.
3. Keep `game-footer` as technical strip or reduce it if chat header replaces visible footer space on mobile.

### Phase 5: Cleanup

1. Split exploration CSS out of generic `viewport.css` if needed.
2. Remove duplicate button shell from combat/exploration CSS.
3. Compile `game_bundle.css` to `game.css`.
4. Verify viewports: 380/428 portrait, 830x380 landscape, 768x1024, 1024x768, 1280x720, 1440x830.

## Risks

- `game.css` currently contains compiled duplicates from several source files. Do not edit it directly.
- `viewport.css` is currently both shared viewport and exploration domain CSS.
- `combat.css` already has real production behavior; prototype must not overwrite data assumptions.
- `btn-node` is shared across site/cabinet/game and should not become the gameplay action button.
- Chat already has production mechanics. Replacing it with prototype mobile chat would be regression.

## Immediate Recommendation

Next code step should not be more prototype-only fixes. The next step should be production-aware extraction:

1. Create production `components/game/action_panel.css`.
2. Import it in `game_bundle.css`.
3. Move/alias `.dp` into `.game-action-button`.
4. Refactor only one production domain first, preferably exploration controls, because its `.dp` surface is already closest to shared behavior.
5. Then refactor combat command deck to the same shared component.

This avoids the current failure mode: designing a usable prototype but then having no clean path into the real Jinja/CSS shell.

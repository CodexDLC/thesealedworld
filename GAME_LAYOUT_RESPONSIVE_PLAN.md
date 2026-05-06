# Game Layout Responsive Plan

## Goal

Create one shared responsive foundation for the game UI before changing individual scenario, exploration, arena, combat, status, inventory, or chat screens.

The shell should define default behavior for screen containers, side panels, center viewport, header, footer, overlays, and scroll rules. Domain CSS should only tune content inside those containers.

## 1. Information Collection: Current Base Layouts

Status: completed as the first shared audit pass.

This phase maps the current game shell before domain-specific refactors. The important result: the live game shell is already centralized around `base_game.html`, `session_content_inner.html`, `layout.css`, and `game_shell.js`, but some domain CSS still duplicates shell/header/menu behavior.

### Files To Inspect

- `src/frontend/templates/game/base_game.html`
- `src/frontend/templates/game/session.html`
- `src/frontend/templates/game/session_content.html`
- `src/frontend/templates/game/session_content_inner.html`
- `src/frontend/templates/game/includes/header.html`
- `src/frontend/templates/game/includes/footer.html`
- `src/frontend/templates/game/domains/game_menu/header_nav.html`
- `src/frontend/static/css/game_bundle.css`
- `src/frontend/static/css/pages/game/layout.css`
- `src/frontend/static/css/pages/game/hud_windows.css`
- `src/frontend/static/css/pages/game/status.css`
- `src/frontend/static/css/pages/game/chat.css`
- `src/frontend/static/css/pages/game/viewport.css`
- `src/frontend/static/css/pages/game/field.css`
- `src/frontend/static/css/pages/game/scenario.css`
- `src/frontend/static/css/pages/game/arena.css`
- `src/frontend/static/css/pages/game/combat.css`
- `src/frontend/static/js/core/game_shell.js`

### Current Container Map

| Container | Current owner | Current behavior | Refactor owner |
| --- | --- | --- | --- |
| `#app-viewport` | `base_game.html`, `layout.css` | Full-height game runtime root, Alpine `gameShell(...)` scope. | Keep in `base_game.html` and shared shell CSS. |
| `#game-header` | `base_game.html`, `session_content.html`, `layout.css` | Top flex header with left brand, center menu, right exit/server/ping. | Shared shell/header work, not domain CSS. |
| `#main-content` | `base_game.html`, `layout.css` | Flex region between header/footer, hides overflow. | Shared shell CSS. |
| `.shell-constrained` | `layout.css` | Width limiter and shell token scope; currently `max-width: 1600px`, `--side-panel-width: 340px`. | Shared shell CSS and `layout_responsive.css`. |
| `.game-session-shell` | `session_content_inner.html` | Session root and background layer parent. | Shared shell template. |
| `.game-top-row` | `session_content_inner.html`, `layout.css`, `game_shell.js` | Three-column grid; `leftOpen/rightOpen` classes control columns. | Shared shell CSS and Alpine state. |
| `.col-left` | `session_content_inner.html`, `layout.css` | Left side panel, scrollable, hidden by default unless open. | Shared shell CSS; domain owns inner content only. |
| `.col-center` | `session_content_inner.html`, `layout.css` | Center viewport column, protects central content. | Shared shell CSS. |
| `.col-center-inner` | `session_content_inner.html`, domain templates | Domain content wrapper inside center viewport. | Shared shell CSS for sizing; domain CSS for inner layout. |
| `.col-right` | `session_content_inner.html`, `layout.css` | Right side panel, hidden by default unless open. | Shared shell CSS; domain owns inner content only. |
| `#game-shell-overlays` | `base_game.html`, `session_content.html` | Modal/HUD root; inventory window lives here. | Shared shell/overlay CSS. |
| `.hud-window` | `hud_windows.css` | Floating draggable/resizable HUD window. | Shared HUD layer, responsive via shared shell tokens. |
| `#game-chat-shell` | `base_game.html`, `session_content.html`, `layout.css`, `chat.css` | Fixed floating chat overlay. | Shared chat/shell coordination. |
| `.game-footer` | `base_game.html`, `session_content.html`, `layout.css` | Bottom shell footer with copyright/status text. | Shared footer work. |

### Current Breakpoints Confirmed

- `layout.css`: `1024`, `768`, `500`.
- `combat.css`: `1120`, `860`.
- `arena.css`: `760`.
- `viewport.css`: `760`.
- `hud_windows.css`: `768`.
- `inventory.css`: `720`.
- global/layout responsive files: `960`, `500`, `480`.

### Current Conflicts Confirmed

- `game.css` is compiled output and must not be edited directly.
- `game_bundle.css` is the game CSS source entry.
- `pages/game/layout.css` currently owns live game header/footer shell rules.
- `includes/header.css`, `includes/footer.css`, and `components/navigation.css` are partially drifted from live game templates.
- `pages/game/field.css` currently duplicates game header and center navigation rules, even though those are shell concerns.
- Some generated/bundled files are already dirty in the worktree, so every task must check diffs before editing.

### Phase 1 Conclusion

The base shell should be owned by:

- `src/frontend/templates/game/base_game.html`
- `src/frontend/templates/game/session_content.html`
- `src/frontend/templates/game/session_content_inner.html`
- `src/frontend/templates/game/includes/header.html`
- `src/frontend/templates/game/includes/footer.html`
- `src/frontend/templates/game/domains/game_menu/header_nav.html`
- `src/frontend/static/css/pages/game/layout.css`
- `src/frontend/static/css/pages/game/layout_responsive.css`
- `src/frontend/static/js/core/game_shell.js`

Domain CSS should stop owning:

- `.game-header`
- `.game-footer`
- `.center-nav`
- `.cnav-btn`
- `.game-menu-icon`
- `.game-top-row`
- `.col-left`
- `.col-center`
- `.col-right`

These selectors are now treated as shared shell selectors.

## 2. Shared Shell Foundation

Status: initial shared foundation created.

Created/updated source files:

- `src/frontend/static/css/pages/game/layout.css`: base desktop-first shell model.
- `src/frontend/static/css/pages/game/layout_responsive.css`: media queries and shell token overrides.
- `src/frontend/static/css/game_bundle.css`: import `layout_responsive.css` from the source bundle.

Base shell tokens to define:

- `--side-panel-width`
- `--side-panel-width-compact`
- `--center-content-max`
- `--game-header-height`
- `--game-footer-height`
- `--game-ui-scale`
- `--game-panel-z`
- `--game-overlay-z`
- `--game-drawer-width`

Implemented shell breakpoint model:

- `>=1600`: full desktop shell.
- `1440-1599`: compact desktop width tuning.
- `1280-1439`: right panel becomes optional drawer by default.
- `1025-1279`: side panels narrower, center protected.
- `769-1024`: both side panels should be evaluated as drawers, especially for scenario screens.
- `<=768`: both side panels are fixed overlay drawers.
- `<=500`: narrow drawer and compact header/footer spacing.

### New Shared Contract

Feature/domain CSS should use the shared shell instead of redefining panel mechanics:

- left/right panels are shell drawers or columns depending on viewport;
- right panel becomes an overlay drawer below `1440`;
- both panels use drawer mechanics below `1024`;
- panel top/bottom offsets come from `--game-header-height` and `--game-footer-height`;
- side width comes from `--side-panel-width` or `--game-drawer-width`;
- domain content should fit inside `.col-center-inner`;
- scrollable content should stay inside domain-owned content containers, not force shell columns wider.

### Files For Future Workers

Workers adapting individual screens should read:

- this document;
- `src/frontend/static/css/pages/game/layout.css`;
- `src/frontend/static/css/pages/game/layout_responsive.css`;
- the CSS file for their own feature.

They should not edit `src/frontend/static/css/game.css` directly.

## 3. Header And Footer Refactor

Goal: make the top shell cleaner and move technical status out of the header.

### Handoff Task

You are working in `C:\install\projects\pets\TurnBasedMMORPG`.

Read first:

- `GAME_LAYOUT_RESPONSIVE_PLAN.md`
- `src/frontend/static/css/pages/game/layout.css`
- `src/frontend/static/css/pages/game/layout_responsive.css`
- `src/frontend/templates/game/includes/header.html`
- `src/frontend/templates/game/includes/footer.html`
- `src/frontend/templates/game/domains/game_menu/header_nav.html`

Owned files:

- `src/frontend/templates/game/includes/header.html`
- `src/frontend/templates/game/includes/footer.html`
- `src/frontend/static/css/pages/game/layout.css`
- `src/frontend/static/css/pages/game/layout_responsive.css`
- optionally `src/frontend/templates/game/domains/game_menu/header_nav.html` if markup class hooks are needed

Do not edit:

- `src/frontend/static/css/game.css` directly;
- domain CSS files such as `scenario.css`, `combat.css`, `arena.css`, `viewport.css`, unless the task explicitly requires a tiny compatibility fix;
- backend/session logic.

Desktop header target:

- left: game title from the main site brand style, plus version/resonance when useful;
- center: game menu/navigation in one line;
- right: compact user/account control, not a large exit block.

Mobile header target:

- first row or top area: game title;
- second row or centered band: game menu;
- account control remains compact;
- no server/ping clutter in the header.

Footer target:

- server status, online indicator, ping, and system status live in footer;
- copyright can remain low-priority or be removed from gameplay focus if space is tight;
- footer should work on desktop and mobile without stealing much vertical space.

Account control target:

- right-side circular user/account button;
- menu items can include Cabinet, Lobby, Settings later;
- keep `/game-lobby` cleanup behavior available until session cleanup is redesigned.

### Expected Result

- Header no longer carries server online/ping as primary right-side content.
- Desktop header reads as one clean line: brand/title, centered menu, compact account/session control.
- Mobile header can wrap into brand row plus centered menu row without overlap.
- Footer owns technical status: server, online indicator, ping, and system status.
- Existing `/game-lobby` cleanup behavior remains reachable from the account/session control.
- Header/footer dimensions continue to use `--game-header-height` and `--game-footer-height`.

### Verification

- Run `git diff --check`.
- Run focused template tests if available.
- Search for duplicated status placement:
  - `rg "server-status|connection-stats|ping-val|game-exit-link" src/frontend/templates/game src/frontend/static/css/pages/game`
- Manual viewport check at `1440`, `1024`, `768`, `500`.

## 4. Scenario Viewport Adaptation

Goal: adapt the scenario screen to the shared shell without redefining panel/header/footer behavior.

### Handoff Task

You are working in `C:\install\projects\pets\TurnBasedMMORPG`.

Read first:

- `GAME_LAYOUT_RESPONSIVE_PLAN.md`
- `src/frontend/static/css/pages/game/layout.css`
- `src/frontend/static/css/pages/game/layout_responsive.css`
- `src/frontend/templates/game/domains/scenario/viewport/main.html`
- `src/frontend/static/css/pages/game/scenario.css`

Owned files:

- `src/frontend/templates/game/domains/scenario/viewport/main.html`
- `src/frontend/static/css/pages/game/scenario.css`

Do not edit:

- `layout.css` or `layout_responsive.css` unless the shared shell has a confirmed missing token;
- `game.css` directly;
- scenario backend routes/services.

- Use shell tokens for avatar width, copy font size, and inner padding.
- Shrink avatar below `1280`, shrink again below `1024`, stack below `768`.
- Make story text scroll independently when vertical space is constrained.
- Keep choices reachable; either sticky inside the scenario panel or part of the same scroll model.
- Add progressive text reveal later as a small JS behavior, preferably by paragraph/sentence chunks rather than per-letter typing.

### Expected Result

- Scenario panel fits inside `.col-center-inner` at `1440`, `1280`, `1024`, `768`, and `500`.
- Scenario avatar uses responsive variables instead of one hard `340px` block.
- Long text does not push choices below unreachable viewport space.
- Choices remain reachable and usable on narrow widths.
- Scenario CSS no longer makes assumptions about persistent sidebars.

### Verification

- Run `git diff --check`.
- Inspect with long scenario text and 3+ choices.
- Manual viewport check at `1440`, `1280`, `1024`, `768`, `500`.
- Confirm no direct edits to compiled `game.css`.

## 5. Status And Sidebar Content Adaptation

Goal: make left/right panel contents work inside both persistent columns and drawer panels.

### Handoff Task

You are working in `C:\install\projects\pets\TurnBasedMMORPG`.

Read first:

- `GAME_LAYOUT_RESPONSIVE_PLAN.md`
- `src/frontend/static/css/pages/game/layout.css`
- `src/frontend/static/css/pages/game/layout_responsive.css`
- `src/frontend/templates/game/components/status/main.html`
- `src/frontend/templates/game/components/panel/main.html`
- `src/frontend/templates/game/domains/scenario/left_sidebar/main.html`
- `src/frontend/templates/game/domains/exploration/left_sidebar/main.html`
- `src/frontend/templates/game/domains/exploration/right_sidebar/main.html`
- `src/frontend/templates/game/domains/arena/right_sidebar/main.html`
- `src/frontend/static/css/pages/game/status.css`

Owned files:

- `src/frontend/static/css/pages/game/status.css`
- status/sidebar component templates only if markup hooks are missing

Do not edit:

- shell drawer behavior in `layout_responsive.css`;
- scenario/combat/arena viewport CSS;
- compiled `game.css`.

- Side panels should rely on shell drawer behavior.
- Panel internals should scroll with mouse/touch.
- Avatar/card sizes should respond to shell width tokens.
- Attribute grids and skill rows should avoid fixed sizes that overflow narrow drawers.

### Expected Result

- Status panel content fits at `340px`, `320px`, `300px`, and mobile drawer width.
- Avatar, attributes, skills, vitals, and panels remain readable without horizontal overflow.
- `.col-left`/`.col-right` own outer scroll; status internals only add nested scroll where necessary.
- No shell selectors are redefined in `status.css`.

### Verification

- Run `git diff --check`.
- Test with populated status data and missing/empty data states.
- Manual widths: `1440`, `1280`, `1024`, `768`, `500`.

## 6. Exploration, Arena, And Combat Content Cleanup

Goal: make domain content respect the shared shell and remove duplicated shell/header/menu rules from domain CSS.

### Handoff Task

You are working in `C:\install\projects\pets\TurnBasedMMORPG`.

Read first:

- `GAME_LAYOUT_RESPONSIVE_PLAN.md`
- `src/frontend/static/css/pages/game/layout.css`
- `src/frontend/static/css/pages/game/layout_responsive.css`
- `src/frontend/static/css/pages/game/viewport.css`
- `src/frontend/static/css/pages/game/field.css`
- `src/frontend/static/css/pages/game/arena.css`
- `src/frontend/static/css/pages/game/combat.css`
- matching domain templates under `src/frontend/templates/game/domains/`

Owned files:

- `src/frontend/static/css/pages/game/viewport.css`
- `src/frontend/static/css/pages/game/field.css`
- `src/frontend/static/css/pages/game/arena.css`
- `src/frontend/static/css/pages/game/combat.css`
- domain viewport/sidebar templates only if class hooks are missing

Do not edit:

- `layout_responsive.css` except for a clearly documented shell-token bug;
- `header.html`/`footer.html`;
- compiled `game.css`.

- Keep domain-specific composition inside `.col-center-inner`.
- Remove shell/header/nav duplication from domain CSS.
- Use explicit local breakpoints only for domain content, not side-panel behavior.
- Combat may keep stricter focus behavior, but it should still use shared shell tokens where possible.

### Expected Result

- `field.css` no longer owns `.game-header`, `.center-nav`, `.cnav-btn`, or `.game-menu-icon`.
- Exploration/arena/combat layouts fit inside the shell at common widths without horizontal overflow.
- Combat may force domain-specific focus, but it does not redefine generic side-panel mechanics unless documented.
- Domain breakpoints remain about content grids/cards/actions, not shell columns.

### Verification

- Run `git diff --check`.
- Search for shell selector duplication:
  - `rg "\.game-header|\.game-footer|\.center-nav|\.cnav-btn|\.game-menu-icon|\.game-top-row|\.col-left|\.col-right" src/frontend/static/css/pages/game`
- Manual viewport checks for exploration, arena, and combat at `1440`, `1024`, `768`, `500`.
- Run frontend template contract tests if available.

## 7. Chat And HUD Window Coordination

Goal: make floating chat and HUD windows respect shared header/footer/drawer dimensions.

### Handoff Task

You are working in `C:\install\projects\pets\TurnBasedMMORPG`.

Read first:

- `GAME_LAYOUT_RESPONSIVE_PLAN.md`
- `src/frontend/static/css/pages/game/layout.css`
- `src/frontend/static/css/pages/game/layout_responsive.css`
- `src/frontend/static/css/pages/game/chat.css`
- `src/frontend/static/css/pages/game/hud_windows.css`
- `src/frontend/static/js/core/game_shell.js`
- `src/frontend/templates/game/base_game.html`
- `src/frontend/templates/game/session_content.html`

Owned files:

- `src/frontend/static/css/pages/game/chat.css`
- `src/frontend/static/css/pages/game/hud_windows.css`
- `src/frontend/static/js/core/game_shell.js` only if positioning math needs token-aware updates

Do not edit:

- inventory internals unless window body overflow requires a small hook;
- scenario/combat/arena CSS;
- compiled `game.css`.

- Chat should account for header/footer heights and drawer overlays.
- HUD windows should use shared z-index and viewport constraints.
- Inventory window should keep resize/drag behavior on desktop and switch to fixed bottom sheet or drawer behavior on mobile.

### Expected Result

- Chat never overlaps footer controls incoherently.
- HUD windows do not open under header/footer.
- Mobile inventory remains usable as a bottom sheet or fixed panel.
- Desktop drag/resize behavior remains intact.
- z-index usage follows `--game-panel-z` / `--game-overlay-z` where possible.

### Verification

- Run `git diff --check`.
- Manual check chat minimized/expanded at `1440`, `1024`, `768`, `500`.
- Manual check inventory open, drag, resize on desktop.
- Manual check inventory open on mobile width.

## Parallel Work Split After Phase 1

Suggested parallel tasks after the audit is complete:

- Worker A: task 3, header/footer template and shell styling.
- Worker B: task 4, scenario viewport responsive internals.
- Worker C: task 5, status/sidebar responsive internals.
- Worker D: task 6, exploration/arena/combat content checks and duplicate shell selector cleanup.
- Worker E: task 7, chat/HUD window coordination with header/footer/drawer heights.

Each worker should own a disjoint file set and avoid editing compiled `game.css` directly. Static compilation should happen once after integration.

## Verification Plan

- Run static compilation: `python src/frontend/manage.py compile`.
- Run focused frontend template tests.
- Inspect generated `src/frontend/static/css/game.css` only as output.
- Manual viewport checks: `1600`, `1440`, `1280`, `1024`, `768`, `500`.
- Confirm side panel scroll, center content scroll, chat overlay, inventory HUD, and header/footer layout at each width.

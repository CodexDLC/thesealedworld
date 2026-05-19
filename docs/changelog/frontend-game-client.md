# Frontend / Game Client Changelog

Detailed milestone history for browser-facing gameplay surfaces inside
`src/frontend`.

## [Unreleased]

- No gameplay client changes yet for the future `v0.1.0` release.
- Combat outcome screens now support spectating mode with summary and log tabs plus an explicit refresh-status action after player death.
- Inventory UI now separates items and resources through tab-aware backend actions and resource-specific icon rendering.

## [v0.0.0] - MVP Baseline

- Game-facing frontend orchestration lives separately from the public site under
  `src/frontend/game_features/`.
- Game views call backend behavior through `src/frontend/integrations/backend_api/`
  instead of importing backend internals.
- Game-token browser state was added for `tbmmorpg_game_access_token` and
  `tbmmorpg_game_refresh_token`.
- Game UI calls now prefer game access tokens, with transitional site-token
  fallback kept only for incremental rollout.
- Lobby, scenario, exploration, combat, arena, inventory, city services, and
  character-status surfaces are being shaped as gameplay client domains.
- Game lobby create, select, release, and delete flows now coordinate with the
  backend game service through typed internal requests.
- Gameplay templates and CSS continue moving toward reusable shell, domain, and
  component layers.
- The game header and gameplay surfaces use **The Sealed World** as the player
  facing product name.

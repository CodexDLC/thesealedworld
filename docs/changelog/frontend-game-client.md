# Frontend / Game Client Changelog

Detailed milestone history for browser-facing gameplay surfaces inside
`src/frontend`.

## [Unreleased]

- Combat UI now localizes archived stat labels, goblin archer names, and effect
  markers instead of showing raw ids in visible battle surfaces.
- Gameplay routes can now run as a dedicated play surface while the public site remains on its own route/middleware set.
- Auth cookies now honor a `auth_cookie_secure` setting so production deploys can pin `Secure`; the refresh cookie is also pinned to `SameSite=Strict` since it is never needed during cross-site navigation.
- Login now always runs the password hashing step against a constant dummy hash when the email is unknown, removing the timing signal that previously exposed user enumeration.
- Registration now requires a 10+ character password that does not contain the email local part, and the email field is validated with `pydantic[email]` instead of the prior naive `@` check.
- Refresh tokens are stored only as `sha256` hashes (`site.auth_refresh_tokens.token_hash`); plaintext column was removed in migration `0002_security_baseline`.
- Frontend now sends baseline security headers on every response (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`, `Permissions-Policy`).
- `/account` redirect to `/account/profile` now returns `303 See Other` instead of `307`, so any future POST traffic is not silently replayed.

## [v0.2.1a2] - Alpha 0.2.1a2

- Game chat now renders outside the footer shell while the footer placement contract is rebuilt.
- Combat viewport controls now expose richer action metadata, inventory slots, and responsive exchanges for the refreshed combat catalog.
- Rift sidebars now surface detailed generated encounter previews from the monster gear-score contract.

## [v0.2.0a1] - Alpha 0.2.0

- Browser gameplay now includes the rift screen, movement state, sidebars, icons, responsive styling, and typed backend API clients for rift play.
- Combat and inventory views now expose updated combat action, gear, quiver, status, and shell presentation data from backend resources.
- Combat log now keeps the newest exchange turns visible after the first eight turns instead of pinning the embedded page to old entries.
- Combat token counters now show only free tokens, while reserved feint costs stay visible on the feint buttons.
- Game shell JavaScript now separates catalog loading, state loading, inventory interactions, and rift state handling into clearer client modules.

## [v0.1.0a1] - First Alpha

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
- Combat outcome screens support spectating mode with summary and log tabs plus
  an explicit refresh-status action after player death.
- Inventory UI separates items and resources through tab-aware backend actions
  and resource-specific icon rendering.

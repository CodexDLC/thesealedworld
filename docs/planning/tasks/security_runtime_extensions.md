# Security Runtime Extensions

Status: expected.

The AuthX access-token migration is complete enough to remove the old migration
task. This task tracks the next security-runtime extensions that still need
explicit design and implementation.

## Current Baseline

- Access JWT creation and validation use AuthX behind project-owned wrappers.
- Route code should use project auth dependencies, not AuthX directly.
- Password hashing remains project-owned.
- Refresh-token persistence remains project-owned and opaque.
- Browser auth cookies are currently owned by the frontend/site flow.

## Scope

This task covers future security runtime work:

- protected route coverage for game/API endpoints;
- browser cookie ownership and CSRF policy;
- access-token revocation/blocklist strategy;
- refresh-token revoke semantics;
- social login and local user linking;
- roles/scopes authorization for admin, internal, and game-master surfaces.

## Phase 1: Protected Route Coverage

- [ ] Add targeted tests for protected game/API routes.
- [ ] Verify `require_game_character_scope()` is applied where character-owned game APIs receive `character_id` / `char_id`.
- [ ] Verify unauthenticated requests fail consistently.
- [ ] Verify authenticated users cannot access another user's character scope.

## Phase 2: Browser Cookies And CSRF

- [ ] Decide whether backend API or frontend BFF owns auth cookies long term.
- [ ] Preserve current frontend cookie behavior until a replacement is proven.
- [ ] If AuthX cookie helpers are used, configure project cookie names explicitly.
- [ ] Enable CSRF for unsafe browser methods when cookie auth is enabled.
- [ ] Keep local-dev secure-cookie behavior configurable.

Acceptance:

- [ ] Login sets the expected HttpOnly cookies.
- [ ] Refresh works through browser flow.
- [ ] Unsafe requests without CSRF fail when cookie auth is enabled.
- [ ] Unsafe requests with CSRF pass.

## Phase 3: Logout, Revoke, And Blocklist

- [ ] Add token revocation storage strategy.
- [ ] Prefer storing token hash or `jti`, not raw token text.
- [ ] Wire AuthX blocklist callback if it fits the selected strategy.
- [ ] Decide Redis-first vs DB-first source of truth.
- [ ] Keep current refresh-token deletion behavior until new revoke logic is tested.

Acceptance:

- [ ] Logout invalidates refresh token.
- [ ] Revoked access token is rejected.
- [ ] Revoked refresh token is rejected.
- [ ] Revocation entries expire or are cleaned up.

## Phase 4: Social Login And Local User Linking

- [ ] Add feature-owned social identity model.
- [ ] Add provider identity repository/integration.
- [ ] Use Authlib or a dedicated provider client for browser OAuth flow.
- [ ] Link external provider identity to local `User`.
- [ ] Do not allow provider identity to become the project user model.

Possible model:

```text
auth_social_identities
  id
  user_id
  provider
  provider_user_id
  email_at_link_time
  created_at
  updated_at
```

Acceptance:

- [ ] Google identity can create or link a local user.
- [ ] Facebook identity can create or link a local user.
- [ ] Duplicate provider identity is rejected.
- [ ] OAuth state/nonce is validated.
- [ ] Local login still works.

## Phase 5: Roles And Scopes Authorization

Do not implement this phase before token validation, browser flow, and revoke
behavior are stable. Roles/scopes affect authorization policy, not only token
mechanics.

The project owns:

- role storage;
- role assignment rules;
- scope naming;
- stale-token behavior;
- endpoint ownership;
- audit/logging policy.

Proposed scope names:

- `admin:*`
- `admin:users`
- `admin:settings`
- `internal:*`
- `internal:health`
- `game-master:*`
- `game-master:characters`
- `game-master:combat`
- `account:read`
- `account:write`

Checklist:

- [ ] Decide whether roles are a simple enum, DB table, or hybrid.
- [ ] Add role-to-scope mapping in the auth feature, not in AuthX config.
- [ ] Add migration for role storage if DB-backed.
- [ ] Add auth dependency wrappers such as `require_scope()` and `require_admin()`.
- [ ] Keep route code importing project wrappers, not AuthX directly.
- [ ] Include scopes when issuing access tokens.
- [ ] Decide whether refresh-created access tokens re-read roles from DB.
- [ ] Decide how role changes revoke or age out existing access tokens.
- [ ] Add audit logs for denied privileged requests.
- [ ] Apply wrappers to admin/internal/game-master endpoints only after tests exist.

Risks:

- Scopes inside JWT can become stale after role changes.
- A wildcard scope such as `admin:*` is powerful and must be issued narrowly.
- Game-master permissions may need character/world-specific constraints, not only
  global scopes.
- Frontend visibility checks must not replace backend authorization.

# AuthX Security Runtime Migration

Date: 2026-05-07

## Status

Implementation task in progress.

Goal: adopt `authx==1.6.0` as the security runtime for token creation and validation while keeping the auth domain owned by `src/backend/features_site/auth`.

This task intentionally stops before roles/scopes implementation. Roles/scopes are tracked as a later task because they need a separate authorization model decision.

## Decision

Adopt AuthX partially.

AuthX should replace the custom JWT create/decode path, but it must not own:

- `User` model.
- Registration and login business logic.
- Password hashing policy.
- Refresh-token persistence.
- Social identity linking.
- Game-specific authorization.

AuthX is used as an adapter/runtime behind project-owned wrappers.

## Current Context

Important files:

- `src/backend/core/security.py`
- `src/backend/config/settings.py`
- `src/backend/features_site/auth/`
- `src/frontend/site_features/auth/`
- `src/frontend/integrations/backend_api/auth.py`
- `src/frontend/game_features/session/`
- `src/backend/core/security.py`
- `src/backend/chat/api/ws.py`

Current behavior:

- Access JWT is hand-written in `src/backend/core/security.py`.
- Password hashing is also in `src/backend/core/security.py`.
- Refresh tokens are opaque random strings stored in `auth_refresh_tokens`.
- Frontend BFF stores access and refresh tokens in HttpOnly cookies.
- Chat has a separate copy of JWT decode logic.

## Target Shape

Add an AuthX adapter under the auth feature:

```text
src/backend/features_site/auth/
  security/
    authx_config.py
    authx_runtime.py
    token_service.py
    blocklist.py
    csrf.py
```

Responsibilities:

- `authx_config.py`: map project settings to `AuthXConfig`.
- `authx_runtime.py`: create the feature-owned `AuthX` instance.
- `token_service.py`: expose project methods such as `create_access_token()` and `decode_access_token()`.
- `blocklist.py`: later integration for revoked token checks.
- `csrf.py`: later cookie/CSRF policy for browser flow.

Keep `src/backend/core/security.py` as a compatibility wrapper during the first migration step. Do not move user business logic into AuthX.

## Phase 1: AuthX Access JWT Runtime

- [x] Add `authx==1.6.0` after explicit dependency approval.
- [x] Add AuthX settings to `BackendSettings`.
- [x] Create feature-owned AuthX config/runtime files.
- [x] Change `create_access_token()` to use AuthX.
- [x] Change `decode_access_token()` to use AuthX.
- [x] Keep current password hashing unchanged.
- [x] Keep current refresh-token DB flow unchanged.

Acceptance:

- [x] `/auth/login` returns an access token signed by AuthX.
- [x] `/auth/me` accepts the new access token.
- [x] Expired access tokens are rejected.
- [x] Invalid signatures are rejected.
- [x] Existing auth service tests still pass after focused updates.

Rollback:

- Revert only the wrapper implementation in `src/backend/core/security.py` / auth security adapter.
- Keep refresh-token persistence untouched, so rollback does not require DB changes.

## Phase 2: Protected Backend Dependencies

- [x] Keep `get_current_user()` as the public dependency for route code.
- [x] Hide AuthX `TokenPayload` inside auth dependencies.
- [x] Ensure feature routers still receive project `User` objects.
- [ ] Add targeted tests for protected game/API routes.

Acceptance:

- [x] Backend feature code does not import AuthX directly.
- [x] Game/API routes continue to depend on auth feature wrappers.
- [x] Cached user lookup behavior still works.

Rollback:

- Point the dependency wrapper back to the old decoder.

## Phase 3: Browser Cookies And CSRF

- [ ] Decide whether backend API or frontend BFF owns auth cookies.
- [ ] Preserve current frontend behavior until the decision is implemented.
- [ ] If AuthX cookie helpers are used, configure project cookie names explicitly.
- [ ] Enable CSRF for unsafe browser methods.
- [ ] Keep local-dev secure-cookie behavior configurable.

Acceptance:

- [ ] Login sets the expected HttpOnly cookies.
- [ ] Refresh works through browser flow.
- [ ] Unsafe requests without CSRF fail when cookie auth is enabled.
- [ ] Unsafe requests with CSRF pass.

Rollback:

- Keep the current frontend cookie writer until AuthX cookie behavior is proven.

## Phase 4: Logout, Revoke, And Blocklist

- [ ] Add token revocation storage strategy.
- [ ] Prefer storing token hash or `jti`, not raw token text.
- [ ] Wire AuthX `set_token_blocklist()` callback.
- [ ] Decide Redis-first vs DB-first source of truth.
- [ ] Keep current refresh-token deletion behavior until new revoke logic is tested.

Acceptance:

- [ ] Logout invalidates refresh token.
- [ ] Revoked access token is rejected.
- [ ] Revoked refresh token is rejected.
- [ ] Revocation entries expire or are cleaned up.

Rollback:

- Disable blocklist callback and fall back to current refresh-token deletion.

## Phase 5: Google/Facebook Login And Local User Linking

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

Rollback:

- Disable social provider routes/config.
- Local auth remains unchanged.

## Phase 6: Roles And Scopes Authorization Task

Do not implement this phase before phases 1-5 are stable. This phase is intentionally expanded here as a future task because roles/scopes affect authorization policy, not only token mechanics.

### Goal

Add project-owned role/scope authorization on top of AuthX token validation for admin, internal, and game-master surfaces.

AuthX may carry and validate scopes in access tokens, but the project must own:

- role storage;
- role assignment rules;
- scope naming;
- stale-token behavior;
- endpoint ownership;
- audit/logging policy.

### Proposed Scope Names

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

### Proposed File Shape

```text
src/backend/features_site/auth/
  models/
    role.py
    user_role.py
  repositories/
    role_repository.py
  integrations/
    authorization.py
  services/
    authorization_service.py
  dependencies.py
  security/
    scopes.py
```

Optional frontend follow-up:

```text
src/frontend/site_features/cabinet/
src/frontend/site_features/auth/
```

### Implementation Checklist

- [ ] Decide whether roles are a simple enum, DB table, or hybrid.
- [ ] Add role-to-scope mapping in auth feature, not in AuthX config.
- [ ] Add migration for role storage if DB-backed.
- [ ] Add auth dependency wrappers such as `require_scope()` and `require_admin()`.
- [ ] Keep route code importing project wrappers, not AuthX directly.
- [ ] Include scopes when issuing access tokens.
- [ ] Decide whether refresh-created access tokens re-read roles from DB.
- [ ] Decide how role changes revoke or age out existing access tokens.
- [ ] Add audit logs for denied privileged requests.
- [ ] Apply wrappers to admin/internal/game-master endpoints only after tests exist.

### Risks

- Scopes inside JWT can become stale after role changes.
- A wildcard scope such as `admin:*` is powerful and must be issued narrowly.
- Game-master permissions may need character/world-specific constraints, not only global scopes.
- Frontend visibility checks must not replace backend authorization.

### Tests

- [ ] Normal user is rejected from admin endpoint.
- [ ] Admin user with `admin:*` is accepted.
- [ ] Specific scope works without wildcard.
- [ ] Missing scope returns 403/401 consistently.
- [ ] Role change behavior is tested: old token revoked or naturally expires.
- [ ] Frontend cabinet/admin visibility matches backend result.

### Rollback

- Remove scope dependencies from privileged routes.
- Keep AuthX token validation active.
- Fall back to current `is_superuser` checks while preserving role tables for later cleanup.

## Open Questions

- Should AuthX handle refresh JWTs, or should the project keep opaque refresh tokens?
- Should browser cookies be owned by backend API or frontend BFF?
- Should access tokens include only `sub` in phase 1?
- Should revoked tokens be stored in Redis, DB, or both?
- Should old hand-written access tokens remain valid for a transition window?

## Verification Commands

Focused checks for implementation phases:

```powershell
uv run pytest tests/backend/core/test_security.py tests/backend/features/auth --no-cov
uv run pytest tests/frontend/site_features/auth --no-cov
uv run pytest tests/chat --no-cov
```

Full gate before declaring implementation complete:

```powershell
uv run python tools/dev/check.py --ci
```

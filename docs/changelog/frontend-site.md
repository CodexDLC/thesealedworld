# Frontend / Site Service Changelog

Detailed milestone history for the `src/frontend` site-web layer.

## [Unreleased]

- Production deploy now wires the site and play frontend surfaces separately,
  including Nginx host routing for the `play` domain and realtime websocket proxying.
- Combat generated-image links are normalized back to `/static/generated-assets/...`
  for the play domain, and feint tooltips render catalog HTML only on trusted entries.

## [v0.4.0] - Alpha 0.4.0

### Auth And Security

- Site auth now stores refresh tokens as `sha256` hashes, validates stronger
  registration passwords and `pydantic[email]` addresses, uses a constant dummy
  password hash for unknown-email login attempts, and exposes secure-cookie
  controls for production deploys.
- Every browser surface now receives baseline security headers and double-submit
  CSRF protection, with shared meta/hidden-field rendering and a small
  JavaScript shim for fetch/HTMX requests.
- Site Alembic adds migrations for the security baseline, referral ownership,
  and feature-flagged email verification tokens.

### Accounts And Invitations

- Each account now owns a stable referral code, registration accepts invite
  codes through a 30-day cookie or explicit form field, and signup rewards are
  recorded transactionally without failing unknown-code registrations.
- Account profile now includes the refreshed security, referral, status, and
  copy-to-clipboard surfaces, including masked email display and live referral
  counters.
- Email verification and email-change flows are implemented behind
  `enable_email_verification`, with hashed 24-hour tokens, POST confirmation
  pages, and refresh-token invalidation after successful email change.

### Public Site And Cabinet

- The public site now marks the product honestly as alpha, adds a support page,
  replaces the standalone `/about` page with a `/library` redirect, and ships a
  temporary library stub until the full lore/library surface is ready.
- Landing, footer, navigation, auth modal, feedback, and play-unavailable pages
  were refreshed for the current site idea and tester-entry flow.
- News management now uses a deterministic local cover library with bundled
  PNG/WebP assets instead of the removed generation-AI cover workflow, and the
  shared cabinet article form styling was tightened.

### Routing And Deployment

- Frontend routing can now run the public site surface independently from gameplay routes for layer-specific production rollout.
- Local compose and Nginx test configuration now cover the separated site/play
  routing shape used by the release rollout.

## [v0.2.1a2] - Alpha 0.2.1a2

- Combat AI cabinet tools now expose refreshed simulation controls and family-pressure result metadata for the gear-score balance pass.

## [v0.2.0a1] - Alpha 0.2.0

- Cabinet now exposes combat AI simulation, training, report browsing, PvE family-pressure batch launch, and survival-chart detail workflows.
- Combat AI cabinet run details now show database/Redis storage status instead of local artifact paths.
- Editable game settings now render backend-owned labels, descriptions, risk badges, groups, and numeric min/max hints.
- Account/player cabinet tools now inspect accounts, characters, generated player projections, and character detail surfaces.
- Content operations gained generated-content maintenance controls and richer generated monster inspection/regeneration workflows.

## [v0.1.0a7] - Alpha 7

- Generated asset serving now redirects S3-backed assets to presigned object URLs instead of buffering images through the site process.
- Cabinet static asset versioning is cached after the first filesystem check per process.
- Generated monster cabinet rows now drill down into individual member detail pages with generated text and visual metadata.
- Content cabinet generated-monster pages now filter families by family tier and expose bulk image regeneration actions.
- Player analytics cabinet now shows registered account and created character totals separately.
- Site analytics cabinet now uses current lobby routes, site user totals, and backend session APIs for active counters.

## [v0.1.0a4] - Alpha 4

- Cabinet now includes a news-management module for listing, creating, editing,
  publishing, and deleting site news articles.
- Cabinet article forms use shared static styling for consistent admin
  workflows.
- Site, account, cabinet, and game shells now preload view stylesheets and
  critical self-hosted font assets for faster first paint.
- Cabinet action routes now use the runtime `Request` import expected by the
  action routing layer.

## [v0.1.0a3] - Alpha 3 Production Patch

- Public landing imagery now serves compressed WebP variants with fallbacks and LCP priority hints.
- Site, account, cabinet, and game shells now use self-hosted fonts plus a root favicon route.

## [v0.1.0a1] - First Alpha

- Site ownership is centered on public pages, auth, account, cabinet, library,
  server-rendered templates, frontend routes, and the `site` database schema.
- Auth models, repositories, DTOs, persistence, token/security runtime, API
  routes, and middleware moved into frontend/site ownership.
- Frontend Alembic and database infrastructure exist under
  `src/frontend/alembic/`, `src/frontend/alembic.ini`, and
  `src/frontend/core/database/`.
- Backend auth proxying was removed; site auth is local to the site service.
- Site-to-game calls use typed backend API clients and configured internal
  service keys.
- Site-owned features now live under `src/frontend/features/`, including auth,
  account, cabinet, feedback, public site, email, surveys, and analytics-related
  surfaces.
- Public website branding is aligned around **The Sealed World**.
- Account and email flows gained production-oriented settings such as SMTP
  configuration and secure-cookie controls.
- The root README, production env templates, and changelog links now document the
  first alpha operating model.
- Account and cabinet shell styling aligns with the updated dock navigation and
  responsive layout pass.
- Site Alembic starts from a first-alpha site schema baseline; future schema
  changes should be added as follow-up revisions.

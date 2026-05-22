# Frontend / Site Service Changelog

Detailed milestone history for the `src/frontend` site-web layer.

## [Unreleased]

- Content cabinet generated-monster pages now filter families by family tier and expose bulk image regeneration actions.

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

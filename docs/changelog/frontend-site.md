# Frontend / Site Service Changelog

Detailed milestone history for the `src/frontend` site-web layer.

## [Unreleased]

- Added the root README as the private MVP project entry point.
- Added baseline changelog links for site, backend, and game client layers.
- Added production env documentation through `.env.example`.

## [v0.0.0] - MVP Baseline

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

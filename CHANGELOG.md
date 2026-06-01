# Changelog

This root changelog is the short release view for **The Sealed World**.

This changelog records meaningful product and architecture milestones, not every
small fix. Package versions are resolved from git tags through `hatch-vcs`; a
tag such as `v0.1.0a1` builds package version `0.1.0a1`.

Full layer changelogs live in:

- [Backend / game service](docs/changelog/backend.md)
- [Frontend / site service](docs/changelog/frontend-site.md)
- [Frontend / game client](docs/changelog/frontend-game-client.md)

## [Unreleased]

## [v0.2.0a1] - Alpha 0.2.0

### Product

- Adds the rift runtime and browser client as the next exploration surface, including portal/session state, movement screens, maintenance tooling, and scenario entry content.
- Adds combat AI simulation, policy training, PvE family-pressure diagnostics, and survival-chart cabinet workflows for balancing live-like combat.
- Expands cabinet operations with account/player inspection, editable game settings, generated-content maintenance, and richer runtime analytics.

### Runtime

- Reworks combat catalog resources, feints, triggers, stat assembly, resolver steps, tactical AI, tunable game config, and post-combat routing.
- Adds starter imprint assignment/materialization, single active-character session enforcement, refreshed monster generation resources, and safer post-combat loot handling.

### Docs And Tooling

- Adds stable documentation for combat AI and Redis-backed game config, rift planning/reference updates, game config audit tooling, and generated-monster rebuild tooling.

## [v0.1.0a7] - Alpha 7

### Content Operations

- Adds the cabinet Content Ops section for generated monster families, member
  detail inspection, image regeneration actions, and news cover AI workflow
  wiring.
- Keeps generated asset URLs stable under `/static/generated-assets/...` while
  allowing production bytes to live in S3-compatible object storage.
- Adds production asset backfill tooling with dry-run and skip-existing modes.

### Release And Deploy

- Production deployment now builds and deploys the Telegram bot as its own
  release image/layer instead of leaving it only in the local Docker Compose
  stack.
- Telegram news announcements now use a persistent media sender that can replace
  or delete channel posts through the shared sender coordinate storage.
- Generated image validation now rejects visible text through the Google GenAI
  SDK path used by the production AI provider.

## [v0.1.0a6] - Alpha 6

### Telegram And News

- Adds the Telegram bot/community feed runtime for news auto-publishing,
  announcement delivery, and moderated community group stream handling.
- Adds a local Docker Compose service for running the Telegram bot against the
  development Redis/backend stack.
- Publishes site news article events to the `game_events` stream so runtime
  integrations can react to article publication.

### Observability

- Suppresses noisy `uvicorn.access` output through the structured logging
  pipeline while keeping application logs readable in production.

## [v0.1.0a5] - Alpha 5

### Observability

- Adds the structured logging foundation, Prometheus metrics plumbing, and the
  local development observability stack.
- Completes the codebase logging sweep: logger messages now use PascalCase event
  names, structured fields are emitted through `bind()`, and noisy request/page
  traces are kept at debug level.
- Keeps logging infrastructure under `src/shared/infrastructure/` while moving
  business logging call sites to the structured project format.

### Release And CI

- Splits CI so `develop` runs lint and type checks only, while `main` keeps the
  full quality gate, documentation build, and Docker image verification.
- Keeps release image publication on tag/manual workflows while preserving
  Docker build verification on `main`.

### Site And Documentation

- Adds the news-management agent skill with official community links and article
  formatting guidance.
- Reorganizes design and planning documentation sources.
- Keeps cabinet framework documentation bundled with the package.

### Performance

- Reduces the public site font critical path and keeps render-blocking font
  loading lighter for first paint.

## [v0.1.0a4] - Alpha 4

### Site And Cabinet

- Adds the cabinet news-management module with article CRUD surfaces and
  shared cabinet form styling.
- Keeps cabinet action routes aligned with the runtime request import contract.

### Release And CI

- Extends CI push coverage to the `develop` branch.
- Keeps Ruff type-checking import rules aligned with the current FastAPI
  runtime import patterns.

## [v0.1.0a3] - Alpha 3 Production Patch

### Fixed

- Ensures the production generated-assets Docker volume is initialized with
  `appuser` ownership before site and game services write generated files.
- Adds a loopback-only production admin tools compose layer for PostgreSQL and
  Redis inspection over SSH tunnels.
- Hardens production Nginx defaults by hiding server tokens and rejecting
  unknown TLS hosts with the default server.

## [v0.1.0a1] - First Alpha

### Product

- Establishes **The Sealed World** as the first playable alpha baseline for the private MVP.
- Includes account, public site, cabinet, library, lobby, exploration, scenario, arena, combat, inventory, city-service, chat, and generation-AI surfaces.
- Adds first-death NPC dialogue routing after respawn, tab-aware inventory resources, exploration skill progression, and combat outcome spectating after player death.

### Architecture

- Keeps the production split around `infra`, `site`, and `game` layers.
- Keeps site ownership in `src/frontend`, game runtime ownership in `src/backend`, and browser gameplay surfaces under frontend game feature boundaries.
- Uses Redis Streams, ARQ workers, active character sessions, and typed frontend-to-backend HTTP clients for cross-layer runtime communication.
- Renames the Python package identity to `thesealedworld` and resolves versions from git tags through `hatch-vcs`.

### Release And Deploy

- Adds production compose layers, layer-specific deployment contract docs, and manual GitHub production deploy flow.
- Adds full production env templates plus a `uv`-friendly secret generator for passwords, service keys, and matching database/Redis URLs.
- Collapses site and game Alembic history into first-alpha baseline migrations; future schema changes should add normal follow-up revisions.
- Production deploy preserves sibling layer containers and accepts immutable image refs from release tags or commit SHAs.

### Documentation

- Adds the private MVP README, root release changelog, layer changelogs, deploy-management docs, and agent skills for release discipline.

### Known Limitations

- This is an alpha release, not a stable public launch.
- SMTP, provider API keys, DNS, TLS issuance, and production image refs must be supplied operationally before rollout.
- S3 asset storage settings are documented, but generated asset storage currently implements the local-volume runtime path.

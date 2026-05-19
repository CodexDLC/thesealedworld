# Changelog

This root changelog is the short release view for **The Sealed World**.

We treat `v0.0.0` as the new MVP baseline. The changelog records meaningful
product and architecture milestones, not every small fix. Package versions are
resolved from git tags through `hatch-vcs`; a tag such as `v0.0.0` builds package
version `0.0.0`.

Full layer changelogs live in:

- [Backend / game service](docs/changelog/backend.md)
- [Frontend / site service](docs/changelog/frontend-site.md)
- [Frontend / game client](docs/changelog/frontend-game-client.md)

## [Unreleased]

This section is the working list for the future `v0.1.0` release. It is allowed
to stay more granular until release prep, when it will be collapsed into a
compact version summary.

### Release Prep

- Renamed the Python package identity to `thesealedworld`.
- Added dynamic package versioning from git tags with `hatch-vcs`.
- Updated `uv.lock` for the dynamic `thesealedworld` package.
- Connected the local repository to `https://github.com/CodexDLC/thesealedworld.git`.

### Environment And Deploy

- Added `.env.prod` as a local-only production env copy ignored by git.
- Added `.env.example` with documented production variables and layer settings.
- Added a `uv`-friendly secret generator for production passwords and service keys.

### Documentation

- Added the root `README.md` as the private MVP project entry point.
- Added layer changelogs for backend, site frontend, and game client frontend.
- Added the changelog release skill for commit-time markers and tag-time summaries.

### Product

- Added first-death NPC dialogue routing after respawn, tab-aware inventory resources, and a spectating combat outcome shell.

### Release And Deploy

- Production deploy now preserves sibling layer containers, and management docs publish the deployment contract for layer-specific rollouts.

## [v0.0.0] - MVP Baseline

### Product

- Kept **The Sealed World** as the public game name and product language.
- Framed the repository as a private MVP product workspace, not an open-source package.
- Defined the repository as a from-scratch product baseline rather than a patch
  history of small migration fixes.

### Architecture

- Continued the service split into three operational layers:
  - `infra`: Postgres, Redis, Nginx, volumes, networks, TLS helpers.
  - `site`: public site, auth, account, cabinet, library, server-rendered web UI.
  - `game`: backend game API, chat/ws, workers, runtime state, game/chat migrations.
- Kept frontend-to-backend communication behind typed HTTP clients under
  `src/frontend/integrations/backend_api/`.
- Kept game runtime ownership in `src/backend` and site ownership in `src/frontend`.

### Release And Deploy

- Uses tag-based release thinking as the target process.

### Documentation

- Uses root and layer changelogs as the target release-note shape.

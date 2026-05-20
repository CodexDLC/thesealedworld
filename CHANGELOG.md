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

No unreleased changes yet.

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

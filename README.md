# The Sealed World

**The Sealed World** is a private MVP workspace for a turn-based MMORPG:
a server-rendered web product, a game backend, and a browser game client built in
one repository while the service boundaries are still being finalized.

This is not an open-source project at this stage. The repository is a product
and engineering workspace for proving the game loop, service split, content
pipeline, deployment model, and visual direction.

## What This Is

The project combines three product surfaces:

- **Site**: public pages, account/auth flow, cabinet/admin surfaces, library, and
  maintenance states.
- **Game client**: browser-rendered gameplay screens for lobby, scenario,
  exploration, combat, arena, inventory, and status surfaces.
- **Game backend**: gameplay APIs, runtime state, workers, chat/ws, world data,
  character ownership, combat, exploration, inventory, scenario, and game events.

The current architectural goal is clear operational separation: the site should
remain available even while the game runtime is restarted or under maintenance.

## Repository Map

- `src/backend/` - game backend, chat ownership, runtime workers, game APIs.
- `src/frontend/` - site-web FastAPI service, templates, auth, account, cabinet,
  and game-facing browser views.
- `src/frontend/game_features/` - browser game orchestration and view models.
- `src/frontend/integrations/backend_api/` - typed site-to-game HTTP boundary.
- `src/shared/` - narrow shared DTOs and contracts.
- `deploy/` - Docker, production compose layers, Nginx, certbot helper flow.
- `docs/tasks/` - active architecture and migration workplans.
- `docs/game-design/` - world, RPG, combat, economy, interface, and scenario design.
- `docs/ru/` - Russian technical documentation.
- `docs/changelog/` - detailed layer history.

## Start Here

- [Service split finalization](docs/tasks/service_split_finalization.md)
- [Backend game workplan](docs/tasks/service_split_backend_game.md)
- [Frontend site workplan](docs/tasks/service_split_frontend_site.md)
- [Deployment management](docs/ru/management/deployment.md)
- [Testing strategy](docs/TESTING_STRATEGY.md)
- [Root changelog](CHANGELOG.md)

## Layer Changelogs

- [Backend / game service](docs/changelog/backend.md)
- [Frontend / site service](docs/changelog/frontend-site.md)
- [Frontend / game client](docs/changelog/frontend-game-client.md)

## Release Model

The package name is `thesealedworld`. Versions come from git tags through
`hatch-vcs`; for example, `v0.0.0` builds as package version `0.0.0`.

The first baseline is `v0.0.0`. Changelogs describe meaningful product,
architecture, and layer milestones rather than every small fix.

Release images are intended to be tagged by both release version and commit SHA.
Production deployment is manual and layer-based: `infra`, `site`, `game`, or
`full`.

## Philosophy

The MVP favors a coherent game-product loop over isolated demos. Site, account,
game client, backend runtime, content generation, and deployment are designed as
separate layers, but they are developed together until the boundaries are proven.

The long-term shape is a resilient web game: the site remains stable, the game
runtime can evolve independently, and player-facing screens stay tied to real
game state rather than static mockups.

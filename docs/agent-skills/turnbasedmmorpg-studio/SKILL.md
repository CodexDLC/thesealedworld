---
name: turnbasedmmorpg-studio
description: Studio (local-only analytical cabinet) architecture, source-switcher contract, read-only-on-prod policy, module-migration rules. Use when adding or editing src/studio/* modules, wiring backend API calls in studio, adding a new data source (local / prod / NEON snapshot), or deciding whether a cabinet module belongs in prod frontend vs studio.
---

# TurnBasedMMORPG Studio

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-studio/references/studio-architecture.md`
- `docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md` (studio mirrors frontend layout)
- `docs/agent-skills/turnbasedmmorpg-cabinet-design/SKILL.md` (studio uses the same cabinet UI surface)

If backend API contracts are involved, also use `turnbasedmmorpg-backend`.
If the task is in the design-system layer, also use `turnbasedmmorpg-design-system`.

## What Studio Is

Studio is a **second frontend application** under `src/studio/`, structurally
mirroring `src/frontend/` (own `app.py`, `cabinet.py`, `features/`, `templates/`,
`static/`, `integrations/`). It hosts the **analytical cabinet** — heavy data
exploration views and historical aggregates that have no place on the prod
admin surface.

- Runs on **port 9100**, locally only.
- **Never deployed to prod.** `deploy/compose.site.yml`, `compose.game.yml`,
  `compose.infra.yml`, `compose.tg-bot.yml` do not reference studio.
  `deploy/frontend/Dockerfile` and `deploy/backend/Dockerfile` use whitelisted
  `COPY src/<dir>` and never copy `src/studio/`.
- Lives in the local dev stack only via the `studio` service in
  `deploy/docker-compose.yml`.

## Why It Exists

The prod admin cabinet (`src/frontend/features/cabinet/`) used to host both
live-ops and analytical modules. Analytical modules:

- triggered heavy `GROUP BY` queries on prod Postgres on every page open;
- enlarged the prod attack surface (more endpoints behind the admin gate);
- slowed iteration — any dashboard change required a prod release.

Studio extracts the analytical modules into a separate frontend so that:

1. Prod cabinet stays slim and live-ops-focused.
2. Heavy reads happen against a developer-controlled data source (local DB
   or a snapshot of prod), not against live prod.
3. Studio can be iterated freely without touching prod.

## What Stays In Prod vs What Goes To Studio

Decide by **load and intent**, not by feature area:

| Prod cabinet (live-ops, light) | Studio (analytical, heavy) |
|---|---|
| Live-publishing (`news_management`) | History of sessions over time |
| Moderation / bans (`accounts`) | Multi-day rollups, drilldowns |
| Live config writes / kill-switches (`game_settings`) | AI simulations |
| Light realtime metrics (`game_server`, `site_analytics`, `player_analytics`) | Large content scans (monsters + omens) |
| Live user comms (`messaging`, `feedback`) | Reports built from historical fact tables |

Rule of thumb:

- **Prod cabinet** answers "what do I do with the system right now."
- **Studio** answers "what do I want to learn from the data."

Current split is committed:

- Prod `CABINET_MODULES` (`src/frontend/cabinet.py`): `news_management`,
  `site_analytics`, `site_ops`, `player_analytics`, `accounts`, `game_server`,
  `game_settings`, `messaging`, `feedback`.
- Studio `CABINET_MODULES` (`src/studio/cabinet.py`): `content_ops`,
  `scenario`, `exploration`, `combat`, `combat_ai_testing`.

## Read-Only-On-Prod Contract

Studio is **strictly read-only against the prod source.** It must not:

- POST to prod endpoints (no triggering image regeneration, AI simulations,
  monster rebuilds, etc.);
- write to prod Postgres or prod Redis;
- enqueue arq jobs on prod queues.

Heavy compute that studio surfaces (AI simulations, monster regeneration) runs
on **local** stacks only, via the developer's local `docker-compose.yml`. The
prod `combat-ai-simulation-worker` in `deploy/compose.game.yml` is gated by
the `combat-ai-simulation` profile and is not part of the default prod
composition.

The future intended workflow for prod data is:

1. A NEON (or pg_dump) **snapshot** of prod Postgres lives as a third source
   alongside `local` and `prod`.
2. Studio's Source Switcher selects between `local`, `prod` (live read-only
   via SSH), and the snapshot.
3. Heavy exploration runs against the snapshot, not against live prod.

Until the snapshot source is in place, treat the live `prod` source as
**hands-off** outside of read paths.

## Source Switcher Contract

`SourceSelectorMiddleware` (`src/studio/features/source_selector/middleware.py`)
attaches a `Source` to every request at `request.state.source`. Resolution
order:

1. Cookie `studio_source` (set by the header dropdown).
2. Fallback: `STUDIO_SOURCE` env var.
3. Default: `local`.

Each `Source` (defined in `src/studio/settings.py`) carries:

- `kind` — `"local"` | `"prod"` (and later `"prod_snapshot"`).
- `api_base` — backend HTTP base URL used by studio cabinet modules.
- `pg_dsn` / `redis_url` — when a future module needs direct DB/Redis reads.
- `ssh_host` / `ssh_forwards` — when the source requires an SSH tunnel.

Backend API clients **must** read the base URL from
`request.state.source.api_base`, not from `frontend.config.settings`:

```python
api = SomeBackendApi(client=client, base_url=request.state.source.api_base)
```

This makes every cabinet module source-aware automatically — switching the
header dropdown changes which backend the module queries on the next request.

## Backend Connectivity

Studio talks to a backend through HTTP. It does **not** import backend
internals, and it does **not** open its own Postgres/Redis pools yet (the
registries exist in `features/sources/` for future use, but no module uses
them today).

- For local source, the backend service in `deploy/docker-compose.yml`
  resolves as `http://backend:8001` (set via `LOCAL_API_BASE` env var).
- For prod source, the API base is `http://host.docker.internal:18001` and
  the developer opens an SSH tunnel manually:

  ```powershell
  ssh -N -L 15432:127.0.0.1:5432 -L 16379:127.0.0.1:6379 -L 18001:127.0.0.1:8001 my_game
  ```

  The `my_game` SSH host alias is the same one `deploy/README.md` documents
  for the project's admin tools (CloudBeaver, RedisInsight).

Studio reuses two pieces from `src/frontend`:

- `src.frontend.core.api.BaseApiClient` — the shared HTTP client base.
- `src.frontend.integrations.backend_api.<client>` — any client that is also
  used by a module still in the prod cabinet (`combat_sessions`,
  `exploration_sessions`, `scenario_sessions`, `game_config`,
  `combat_ai_testing`). These stay in frontend because they have a second
  consumer there; studio imports them by their existing path.

Clients used **only** by studio modules live under
`src/studio/integrations/backend_api/` (currently: `admin_monsters.py`,
`combat_analytics.py`).

## Adding A New Module

Apply the same pattern as the existing five migrated modules:

1. Create `src/studio/features/cabinet/modules/<m>/` with `__init__.py` and
   `cabinet.py`. Add a `CabinetAdmin` subclass that registers itself via
   `cabinet_site.register(<m>Admin)` at import time.
2. Set `group_label` to a stable Russian phrase so the home-page tiles and
   sidebar group consistently (`Контент`, `Гейм Сервер`, `Аналитика`, etc.).
3. Add the dotted import path to `src/studio/cabinet.py::CABINET_MODULES`.
4. For data the module needs:
   - If the backend already exposes an endpoint, add a typed HTTP client.
     Place it in `src/studio/integrations/backend_api/<client>.py` if only
     studio uses it, or in `src/frontend/integrations/backend_api/` if a prod
     module also uses it.
   - Always pass `base_url=request.state.source.api_base`.
   - Catch `httpx.HTTPStatusError` / `httpx.RequestError` in providers and
     return empty widgets rather than 500ing the dashboard — backend WIP and
     intermittent unavailability must not break the studio shell.
5. If the module needs to render anything other than the default cabinet
   widgets, the template must live in `src/fastapi_cabinet/templates/cabinet/`
   (the library owns the cabinet templates; both frontend and studio share
   them).
6. Run `uv run ruff check src/studio src/frontend && uv run mypy src/studio`
   before committing.

## What Studio Must Not Do

- Must not import from `src.backend.*` directly (always go through HTTP API,
  even for read-only data).
- Must not write to any source. Even for `local`, treat the source as
  read-only by convention; the studio is for analysis, not data entry.
- Must not couple cabinet modules to a specific source kind. A module must
  work against `local`, `prod`, and future `prod_snapshot` interchangeably
  via `request.state.source.api_base`.
- Must not be added to any `deploy/compose.*.yml` other than the local
  dev `docker-compose.yml`.
- Must not register routes that mutate prod state when the active source is
  `prod`. (When the read-only guard middleware lands, this will be enforced
  in code; until then it's a contract the module authors must respect.)

## Running Locally

Studio comes up automatically with the rest of the local dev stack:

```powershell
docker compose -f deploy/docker-compose.yml up -d --build
```

- Studio: <http://127.0.0.1:9100>
- Prod cabinet: <http://127.0.0.1:8000/admin>

For fast iteration without docker:

```powershell
uv run uvicorn src.studio.app:app --host 127.0.0.1 --port 9100 --reload
```

The local studio container has `--reload` and host-mounted source volumes, so
Python changes to `src/studio`, `src/frontend`, `src/fastapi_cabinet`, and
`src/shared` reload without rebuild.

## Diagnosing Backend-Side Failures

If a studio dashboard renders empty or 500s, check whether the backend
endpoint itself is broken before assuming studio is at fault:

```powershell
docker exec tbmmorpg-studio sh -c 'curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Internal-Service-Key: dev-site-to-game-service-key" "http://backend:8001/<endpoint>"'
```

`BackendRequestRejected` in studio logs means the backend returned non-2xx.
`BackendRequestUnavailable` means studio couldn't connect at all. The first
is usually a backend bug (e.g. a renamed column an analytics repository still
references). The second is usually network/DNS or backend not running.

## Quality Gate

When changing studio code:

- `uv run ruff check src/studio src/frontend` must pass.
- `uv run mypy src/studio` must pass.
- For the running smoke pattern, see the test snippet in
  `references/studio-architecture.md`.

Also apply `turnbasedmmorpg-quality-gate` before declaring done, the same way
frontend changes do.

## Stable Documentation Rule

When studio ownership, source-switcher contract, or read-only-on-prod policy
changes, update this skill and the references page. The migration plan that
seeded studio's structure lives in
`C:/Users/prime/.claude/plans/iterative-sleeping-thunder.md` and is a
historical artifact, not stable documentation.

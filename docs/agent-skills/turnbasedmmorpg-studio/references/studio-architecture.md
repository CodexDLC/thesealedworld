# Studio architecture reference

Concrete file paths, runtime contracts, and a smoke-test snippet. Companion
to `../SKILL.md`.

## Folder layout

```
src/studio/
├── app.py                                  FastAPI entry, lifespan, port 9100
├── cabinet.py                              CABINET_MODULES tuple (registered admins)
├── settings.py                             StudioSettings, Source dataclass, SOURCES
├── README.md
│
├── features/
│   ├── shell/
│   │   └── routes.py                       GET /, GET /health (home tiles)
│   ├── source_selector/
│   │   ├── middleware.py                   SourceSelectorMiddleware → request.state.source
│   │   └── routes.py                       POST /studio/source (cookie writer)
│   ├── sources/
│   │   ├── models.py                       Source, SourceKind re-export
│   │   ├── ssh_tunnel.py                   SshTunnelManager (detect mode; manage mode TODO)
│   │   ├── postgres_readonly.py            PostgresPoolRegistry (currently unused)
│   │   └── redis_readonly.py               RedisClientRegistry (currently unused)
│   └── cabinet/
│       └── modules/
│           ├── content_ops/                Монстры + приметы (heavy reads)
│           ├── scenario/                   Сценарные сессии (analytics)
│           ├── exploration/                Exploration сессии (analytics)
│           ├── combat/                     Combat rollups + drilldown
│           └── combat_ai_testing/          AI-симуляции
│
├── integrations/
│   └── backend_api/
│       ├── admin_monsters.py               Used only by content_ops
│       └── combat_analytics.py             Used only by combat
│
├── templates/
│   └── studio/
│       ├── base_studio.html                Extends site/base_cabinet.html
│       └── home.html                       Module tiles grid
│
└── static/                                 Studio-specific overrides (empty by default)

deploy/
├── docker-compose.yml                      Adds 'studio' service to local dev stack
└── studio/
    └── Dockerfile                          Local-only image
```

The studio service in `deploy/docker-compose.yml` host-mounts `src/studio`,
`src/frontend`, `src/fastapi_cabinet`, `src/shared` and runs uvicorn with
`--reload`.

## Configuration surface (studio settings)

`src/studio/settings.py` defines `StudioSettings` (pydantic). Env vars use
the uppercased field name (no prefix). The compose service sets:

| Field | Env var (compose) | Default | Purpose |
|---|---|---|---|
| `studio_source` | `STUDIO_SOURCE` | `local` | Fallback source when cookie is missing |
| `local_api_base` | `LOCAL_API_BASE` | `http://127.0.0.1:8001` | Backend HTTP for local source (compose sets `http://backend:8001`) |
| `local_pg_dsn` | `LOCAL_PG_DSN` | — | Direct Postgres for local source (future use) |
| `local_redis_url` | `LOCAL_REDIS_URL` | — | Direct Redis for local source (future use) |
| `prod_api_base` | `PROD_API_BASE` | `http://127.0.0.1:18001` | Backend HTTP for prod source (compose sets `http://host.docker.internal:18001`) |
| `prod_pg_dsn` | `PROD_PG_DSN` | — | Direct Postgres for prod source (future use) |
| `prod_redis_url` | `PROD_REDIS_URL` | — | Direct Redis for prod source (future use) |
| `prod_ssh_host` | `PROD_SSH_HOST` | `my_game` | SSH alias from `~/.ssh/config` |

A `Source` is built from these settings by `StudioSettings.sources()` and
exposed to every request as `request.state.source`. Future sources (e.g.
`prod_snapshot` pointing at a NEON-hosted dump) are added by extending the
`SourceKind` literal and the `sources()` factory.

## Backend connectivity contract

Backend HTTP base URL: **always** `request.state.source.api_base`.

Authentication header: studio inherits `BaseApiClient` from
`src.frontend.core.api`, which reads the internal-service key/header from
frontend's settings. As long as backend, frontend, and studio agree on
`BACKEND_INTERNAL_SERVICE_KEY`, calls authenticate transparently. No extra
configuration needed in studio.

Studio modules call backend in two patterns:

1. **Use an existing frontend client** when the same endpoint is also used by
   a prod-cabinet module:

   ```python
   from src.frontend.integrations.backend_api.scenario_sessions import ScenarioSessionsApi

   async def _sessions_provider(request: Request) -> TableWidgetMap:
       client: httpx.AsyncClient = request.app.state.backend_http_client
       api = ScenarioSessionsApi(client=client, base_url=request.state.source.api_base)
       try:
           sessions = await api.list_active()
       except (httpx.HTTPStatusError, httpx.RequestError):
           sessions = []
       ...
   ```

2. **Use a studio-owned client** when only studio uses the endpoint:

   ```python
   from src.studio.integrations.backend_api.admin_monsters import AdminMonstersApi
   ```

Both patterns must catch `httpx.HTTPStatusError` and `httpx.RequestError`
inside the provider/handler and return empty widgets on failure. The studio
shell must keep working even when one module's backend endpoint is broken.

## How a request flows

```
Browser GET /admin/scenario
        │
        ▼
SourceSelectorMiddleware → request.state.source = SOURCES[cookie or default]
        │
        ▼
fastapi_cabinet router (mounted at /admin) → ScenarioAdmin.providers["scenario.sessions"]
        │
        ▼
_sessions_provider(request)
        │
        ▼
ScenarioSessionsApi(client, base_url=request.state.source.api_base).list_active()
        │
        ▼
HTTP GET {api_base}/api/internal/scenario/sessions
        │
        ▼
Backend service (resolved as 'backend:8001' inside docker, or via SSH for prod)
```

For prod source, the URL `http://host.docker.internal:18001/...` reaches the
host's SSH-forwarded port 18001, which the developer's SSH session bridges
to prod's backend on `127.0.0.1:8001`.

## Smoke-test snippet

After any studio change, this should pass:

```powershell
cd C:/install/projects/pets/TurnBasedMMORPG
uv run ruff check src/studio src/frontend
uv run mypy src/studio
```

```python
# Functional check (run via: PYTHONPATH=src uv run python -c "...")
from fastapi.testclient import TestClient
from src.studio.app import app

with TestClient(app) as client:
    assert client.get("/health").status_code == 200

    # Home tiles list all registered modules.
    home = client.get("/")
    assert home.status_code == 200
    assert "Studio" in home.text
    assert "/admin/" in home.text  # at least one tile link

    # Source switcher.
    r = client.post("/studio/source", data={"source": "prod", "next_url": "/"}, follow_redirects=False)
    assert r.status_code == 303
    assert "studio_source=prod" in r.headers.get("set-cookie", "")

    # Switched-state badge.
    home_prod = client.get("/", cookies={"studio_source": "prod"})
    assert "PROD READ-ONLY" in home_prod.text
```

## Diagnosing failures

If a dashboard renders empty or 500s:

```powershell
# 1. Is studio reaching backend at all?
docker exec tbmmorpg-studio sh -c 'curl -sf -o - -w "\nHTTP %{http_code}\n" http://backend:8001/health'

# 2. Is the specific endpoint healthy?
docker exec tbmmorpg-studio sh -c 'curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Internal-Service-Key: dev-site-to-game-service-key" "http://backend:8001/api/<endpoint>"'

# 3. If the endpoint returns 500, the backend logs hold the trace:
docker logs tbmmorpg-backend --tail 200 | grep -E "Traceback|Error|<endpoint-fragment>"
```

In studio's own logs:

- `BackendRequestRejected` (line 72 in `src.frontend.core.api`) means backend
  responded with non-2xx. Usually a backend bug or auth mismatch.
- `BackendRequestUnavailable` (line 75) means studio couldn't connect.
  Usually network/DNS, backend not running, or wrong `api_base` configuration.

## SSH tunnel mode

`SshTunnelManager` runs in `detect` mode today. It probes the configured local
ports and, if any are closed, hints with a copy-paste command. It does **not**
open tunnels itself. The `manage` mode (programmatic open via `sshtunnel` or
`asyncssh`) is intentionally a TODO until a studio module actually needs prod
data — picking the SSH library should match what other project tooling already
uses.

## Future extensions (not yet implemented)

- **`prod_snapshot` source** — a NEON-hosted (or local) Postgres dump of prod,
  selected by the dropdown alongside `local` and `prod`. The intended workflow
  for analytics work; see `../SKILL.md` Read-Only-On-Prod section.
- **Read-only guard middleware** — block non-GET requests in studio when
  `request.state.source.kind in {"prod"}`. Defensive layer on top of the
  contract.
- **Local arq workers** — optional studio-owned workers under
  `src/studio/workers/` for heavy compute that should not even hit a local
  backend. Skipped for now because `combat-ai-simulation-worker` already runs
  on the developer's machine via local `docker-compose.yml`.

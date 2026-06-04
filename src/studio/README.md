# Studio — local-only analytical cabinet

Second frontend application that hosts heavy analytics, AI simulations, and
historical aggregation dashboards. **Never deployed to prod.** Reads prod data
through an SSH tunnel using a read-only Postgres role.

Lives alongside `src/frontend` and mirrors its structure (`app.py`,
`cabinet.py`, `features/`, `templates/`, `static/`, `integrations/`).

See the migration plan at
`C:\Users\prime\.claude\plans\iterative-sleeping-thunder.md`.

## Running locally

Studio is part of the **local dev compose** (`deploy/docker-compose.yml`) and
starts automatically with the rest of the stack:

```powershell
docker compose -f deploy/docker-compose.yml up -d --build
```

Then open <http://127.0.0.1:9100/>. The other services come up on their usual
ports (frontend 8000, backend 8001, chat 8002, postgres 5432, redis 6380, mongo
27017, mailpit 8025).

For fast iteration without rebuilding the container you can also run uvicorn
directly:

```powershell
uv run uvicorn src.studio.app:app --host 127.0.0.1 --port 9100 --reload
```

### Prod data via SSH tunnel

To switch the Source Switcher to `prod` you need an SSH tunnel open on the
host. The project already uses the `my_game` host alias for admin tools
(CloudBeaver, RedisInsight — see `deploy/README.md`); studio reuses the same
alias with different forwards:

```powershell
ssh -N -L 15432:127.0.0.1:5432 -L 16379:127.0.0.1:6379 -L 18001:127.0.0.1:8001 my_game
```

The studio container reaches these forwarded ports through
`host.docker.internal` (already configured in `deploy/docker-compose.yml`).
When running studio directly via uvicorn, it reaches them via `127.0.0.1`.

### Prod isolation

Studio is **never deployed to prod**. The prod compose files
(`deploy/compose.site.yml`, `compose.game.yml`, `compose.infra.yml`,
`compose.tg-bot.yml`) do not reference the studio service. The prod
Dockerfiles (`deploy/frontend/Dockerfile`, `deploy/backend/Dockerfile`) use
whitelisted `COPY src/<dir>` and never copy `src/studio/`.

## Configuration

All studio settings live in `src/studio/settings.py` and can be overridden via
the project `.env` file. Prod credentials must be set in `.env` only — never
commit them. The studio runs against `local` by default.

## Source switching

The Source Switcher in the header writes a cookie `studio_source` (`local` or
`prod`) and reloads. `SourceSelectorMiddleware` resolves the cookie on every
request and attaches the active `Source` to `request.state.source`. Repository
factories (`features/sources/postgres_readonly.py`,
`features/sources/redis_readonly.py`) look up the pool/client for that source.

## Adding a new analytical module

Per the migration plan, modules move out of
`src/frontend/features/cabinet/modules/<m>/` into
`src/studio/features/cabinet/modules/<m>/` (one PR per module). The dotted
import path is added to `src.studio.cabinet.CABINET_MODULES`. The module's
`*.cabinet` file registers a `CabinetAdmin` with the global `cabinet_site` at
import time, exactly like the prod cabinet.

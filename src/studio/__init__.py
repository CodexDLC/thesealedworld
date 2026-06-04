"""Studio — second frontend app, local-only.

Hosts the analytical cabinet (combat balance, AI training, scenario/exploration
analytics, player/site analytics, content ops). Never deployed to prod.

Mirrors the structure of `src/frontend/` (own app.py, cabinet.py, features/,
templates/, static/, integrations/). Reuses `src/frontend/templates` and
`src/frontend/static` as a shared design-system base via Jinja fallback paths
and the /static mount.

Connects to prod data sources (Postgres replica, Redis) via SSH tunnel using
the read-only `studio_ro` role.
"""

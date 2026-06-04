"""Studio settings.

Defines available data sources (local DB / Redis, prod replica via SSH tunnel)
and the active source for the running studio instance.

The active source is selected by:
1. Per-request cookie `studio_source` (set via the Source Switcher dropdown).
2. Otherwise falls back to `STUDIO_SOURCE` environment variable.
3. Otherwise defaults to "local".

Source secrets (prod read-only DSN, SSH host) live in the user's local `.env`
only — never committed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from codex_core.settings import BaseCommonSettings
from pydantic_settings import SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent.parent

SourceKind = Literal["local", "prod"]


@dataclass(frozen=True, slots=True)
class Source:
    """Connection coordinates for one data source.

    All host/port values point at *localhost* — when `ssh_host` is set, the
    studio's SSH-tunnel manager opens forwards from the chosen local ports to
    the remote services on `ssh_host`. When `ssh_host` is None, the host
    addresses are used as-is (typical for the local Postgres/Redis).
    """

    kind: SourceKind
    label: str  # Human-readable label shown in the Source Switcher.
    badge_color: str  # CSS color name for the env badge (e.g. "green", "red").
    api_base: str  # Backend HTTP base URL, used by integrations/backend_api/.
    pg_dsn: str  # asyncpg-compatible Postgres DSN (read-only role for prod).
    redis_url: str  # redis-py URL.
    ssh_host: str | None = None  # ~/.ssh/config alias for programmatic tunnel.
    ssh_forwards: tuple[tuple[int, str, int], ...] = field(default_factory=tuple)
    # ssh_forwards: ((local_port, remote_host, remote_port), ...) — applied at
    # startup if ssh_host is set and the local port is not already occupied.


class StudioSettings(BaseCommonSettings):
    """Studio-specific settings inheriting from codex-core base."""

    # Server
    app_host: str = "127.0.0.1"
    app_port: int = 9100

    # Logging
    debug: bool = True
    log_level_console: str = "DEBUG"
    log_level_file: str = "INFO"
    log_rotation: str = "10 MB"
    log_dir: str = "logs"

    # Active source selection — used as fallback when no cookie is present.
    studio_source: SourceKind = "local"

    # Local source — reuses frontend defaults.
    local_api_base: str = "http://127.0.0.1:8001"
    local_pg_dsn: str = "postgresql://tbmmorpg:tbmmorpg_dev@127.0.0.1:5432/tbmmorpg_game"  # pragma: allowlist secret
    local_redis_url: str = "redis://127.0.0.1:6379/0"

    # Prod source — assumes SSH tunnel forwards prod services to localhost.
    # Override every field in `.env` (never commit prod creds).
    prod_api_base: str = "http://127.0.0.1:18001"
    prod_pg_dsn: str = "postgresql://studio_ro@127.0.0.1:15432/tbmmorpg_game"  # pragma: allowlist secret
    prod_redis_url: str = "redis://127.0.0.1:16379/0"
    prod_ssh_host: str = "my_game"  # alias from ~/.ssh/config; same host the
    # project's admin tunnel uses (see deploy/README.md, CloudBeaver / RedisInsight)

    # Reuse frontend static + templates as design-system library.
    frontend_templates_dir: Path = BASE_DIR / "src" / "frontend" / "templates"
    frontend_static_dir: Path = BASE_DIR / "src" / "frontend" / "static"

    # Studio-specific overrides.
    studio_templates_dir: Path = BASE_DIR / "src" / "studio" / "templates"
    studio_static_dir: Path = BASE_DIR / "src" / "studio" / "static"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    def sources(self) -> dict[SourceKind, Source]:
        """Build the source registry from current settings.

        Returned dict is read-only by convention — callers select an entry by
        `SourceKind` and pass the `Source` instance to repository factories.
        """
        return {
            "local": Source(
                kind="local",
                label="LOCAL",
                badge_color="green",
                api_base=self.local_api_base,
                pg_dsn=self.local_pg_dsn,
                redis_url=self.local_redis_url,
            ),
            "prod": Source(
                kind="prod",
                label="PROD READ-ONLY",
                badge_color="red",
                api_base=self.prod_api_base,
                pg_dsn=self.prod_pg_dsn,
                redis_url=self.prod_redis_url,
                ssh_host=self.prod_ssh_host,
                ssh_forwards=(
                    # (local_port, remote_host_on_server, remote_port)
                    (15432, "127.0.0.1", 5432),
                    (16379, "127.0.0.1", 6379),
                    (18001, "127.0.0.1", 8001),
                ),
            ),
        }


settings = StudioSettings()

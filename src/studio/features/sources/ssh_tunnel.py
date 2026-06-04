"""SSH tunnel manager for studio's prod data source.

Two modes, controlled by `mode` argument on `SshTunnelManager`:

- ``detect`` (default, safest): the user manually opens forwards via
  `ssh -L 15432:127.0.0.1:5432 -L 16379:127.0.0.1:6379 -L 18001:127.0.0.1:8001 prod`
  (same workflow as DBeaver today). The manager only checks that the local
  ports are reachable; if not, raises with a copy-pasteable command.

- ``manage`` (programmatic): opens forwards itself via `sshtunnel`. Not yet
  wired — kept as a TODO so the chosen library can be picked deliberately when
  combat-analytics migration starts hitting prod data.

The default ``detect`` mode is sufficient for the infrastructure-prep PR.
Studio boots with no prod queries; users only need a live tunnel when they
switch the Source Switcher to `prod`.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Iterable

    from src.studio.features.sources.models import Source

Mode = Literal["detect", "manage"]


@dataclass(frozen=True, slots=True)
class TunnelCheckResult:
    """Outcome of probing one source's forwards."""

    source: Source
    ok: bool
    missing_ports: tuple[int, ...]
    cli_command: str  # Hint the user can copy-paste to open the tunnel.


def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Return True if a TCP connection to (host, port) succeeds within timeout."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
        except OSError:
            return False
        return True


def _build_cli_command(source: Source) -> str:
    """Compose an `ssh -L ... <host>` line covering all configured forwards."""
    if not source.ssh_host or not source.ssh_forwards:
        return ""
    forwards = " ".join(
        f"-L {local}:{remote_host}:{remote_port}" for local, remote_host, remote_port in source.ssh_forwards
    )
    return f"ssh {forwards} {source.ssh_host}"


class SshTunnelManager:
    """Per-app lifecycle handle for SSH forwards used by studio sources.

    Held on `app.state.ssh_tunnel`; checked from middleware before serving
    a request that targets a tunnelled source.
    """

    def __init__(self, *, mode: Mode = "detect") -> None:
        self._mode = mode

    async def ensure(self, source: Source) -> TunnelCheckResult:
        """Verify that the forwards for `source` are usable.

        In ``detect`` mode we only probe local ports. In ``manage`` mode we
        would lazily open forwards via `sshtunnel`, but that path is not yet
        implemented (see module docstring).
        """
        if source.ssh_host is None or not source.ssh_forwards:
            return TunnelCheckResult(source=source, ok=True, missing_ports=(), cli_command="")

        missing = tuple(
            local for local, _remote_host, _remote_port in source.ssh_forwards if not _is_port_open("127.0.0.1", local)
        )
        result = TunnelCheckResult(
            source=source,
            ok=not missing,
            missing_ports=missing,
            cli_command=_build_cli_command(source),
        )

        if self._mode == "manage" and missing:
            # TODO: open forwards via sshtunnel.SSHTunnelForwarder / asyncssh.
            # Deferred until a module actually needs prod data — picked
            # deliberately at that point so we can match the SSH client
            # already used by DBeaver/Redis tooling.
            logger.bind(
                ssh_host=source.ssh_host,
                missing_ports=missing,
            ).warning("StudioSshManageModeNotImplemented")

        return result

    async def shutdown(self, sources: Iterable[Source] = ()) -> None:  # noqa: ARG002 (future use)
        """Close any forwards we opened. No-op in ``detect`` mode."""
        return None

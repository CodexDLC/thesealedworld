from io import StringIO
from typing import Any

from loguru import logger
from pydantic import BaseModel
from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table


def log_debug_payload(title: str, payload: Any, *, enabled: bool = True) -> None:
    """
    Render a payload (dict / list / Pydantic model) as a rich table and emit it
    as a single loguru DEBUG message — so the table is not split across many
    timestamped lines.

    Pass `enabled=settings.debug` from the caller to skip work in production.
    """
    if not enabled:
        return

    try:
        if isinstance(payload, BaseModel):
            data: Any = payload.model_dump(mode="json")
        elif hasattr(payload, "model_dump"):
            data = payload.model_dump(mode="json")
        else:
            data = payload

        table = Table(
            title=f"DEBUG PAYLOAD :: {title}",
            show_lines=True,
            title_style="bold magenta",
            header_style="bold cyan",
        )
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="white", overflow="fold")

        if isinstance(data, dict):
            for key, value in data.items():
                rendered = Pretty(value) if isinstance(value, (dict, list)) else str(value)
                table.add_row(str(key), rendered)
        elif isinstance(data, list):
            for idx, value in enumerate(data):
                rendered = Pretty(value) if isinstance(value, (dict, list)) else str(value)
                table.add_row(f"[{idx}]", rendered)
        else:
            table.add_row("(value)", Pretty(data))

        buf = StringIO()
        Console(file=buf, force_terminal=False, width=120, color_system=None).print(table)
        logger.opt(depth=1).debug("\n" + buf.getvalue().rstrip())
    except Exception as e:
        logger.exception(f"Failed to log debug payload '{title}': {e}")

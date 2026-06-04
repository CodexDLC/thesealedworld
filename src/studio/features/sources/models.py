"""Re-export of the Source dataclass used across the sources package.

`Source` is defined in `src.studio.settings` so the env-loading dataclass and
the runtime contract stay in one place. This module exists so callers in
features/sources/* and integrations/* can import `Source` without pulling the
full settings module.
"""

from src.studio.settings import Source, SourceKind

__all__ = ["Source", "SourceKind"]

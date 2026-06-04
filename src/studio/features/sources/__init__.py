"""Data-source connectivity for studio.

Each studio request operates against one `Source` (local / prod read-only).
Modules in this package own:

- `ssh_tunnel`: programmatic SSH-tunnel manager (lifecycle on app startup).
- `postgres_readonly`: asyncpg pool factory keyed by source.
- `redis_readonly`: redis-py client factory keyed by source.

Selection of the active source per request is done by
`src.studio.features.source_selector.middleware.SourceSelectorMiddleware`,
which attaches the chosen `Source` to `request.state.source`.
"""

from src.studio.features.sources.models import Source

__all__ = ["Source"]

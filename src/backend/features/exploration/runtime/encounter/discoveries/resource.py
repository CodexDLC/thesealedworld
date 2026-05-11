from __future__ import annotations

from src.backend.features.exploration.runtime.encounter.discoveries.placeholders import build_placeholder_discovery


async def build_resource_placeholder(*, loc_id: str):
    """TODO(after MVP): generate resource discovery, depletion, and gathering rules."""
    return build_placeholder_discovery(
        discovery_type="resource",
        title="Следы ресурса",
        description="Здесь мог быть найден ресурс, но эта ветка ещё не реализована.",
        loc_id=loc_id,
    )

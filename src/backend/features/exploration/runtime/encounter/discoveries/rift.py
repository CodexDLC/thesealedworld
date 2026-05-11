from __future__ import annotations

from src.backend.features.exploration.runtime.encounter.discoveries.placeholders import build_placeholder_discovery


async def build_rift_placeholder(*, loc_id: str):
    """TODO(after MVP): generate persistent random rift coordinates and entry rules."""
    return build_placeholder_discovery(
        discovery_type="rift",
        title="Следы разлома",
        description="Здесь мог быть найден новый разлом, но эта ветка ещё не реализована.",
        loc_id=loc_id,
    )

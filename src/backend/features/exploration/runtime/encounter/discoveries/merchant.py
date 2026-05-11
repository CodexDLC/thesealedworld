from __future__ import annotations

from src.backend.features.exploration.runtime.encounter.discoveries.placeholders import build_placeholder_discovery


async def build_merchant_placeholder(*, loc_id: str):
    """TODO(after MVP): resolve travelling merchant inventory, prices, and persistence."""
    return build_placeholder_discovery(
        discovery_type="merchant",
        title="Следы торговца",
        description="Здесь могла быть встреча с торговцем, но эта ветка ещё не реализована.",
        loc_id=loc_id,
    )

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.monsters.dto.generation import MonsterLocationContext

if TYPE_CHECKING:
    from src.backend.infrastructure.world.location_store import WorldLocationStore


class MonsterLocationContextIntegration:
    """Read-only monster facade over the world runtime location projection."""

    def __init__(self, world_locations: WorldLocationStore) -> None:
        self.world_locations = world_locations

    async def get_location_context(self, loc_id: str) -> MonsterLocationContext:
        raw = await self.world_locations.get_location(loc_id)
        if not isinstance(raw, dict):
            raise ValueError(f"World location not found: {loc_id}")

        world_zone = raw.get("world_zone")
        if not isinstance(world_zone, dict):
            raise ValueError(f"World location is missing world_zone projection: {loc_id}")

        biome_id = str(world_zone.get("biome_id") or "")
        if not biome_id:
            raise ValueError(f"World location is missing world_zone.biome_id: {loc_id}")

        flags = _dict(raw.get("flags"))
        anchor = _dict(raw.get("anchor_influence"))
        tier = max(
            0,
            min(
                7,
                max(
                    _to_int(world_zone.get("tier")),
                    _to_int(flags.get("threat_tier")),
                    _to_int(anchor.get("tier")),
                ),
            ),
        )
        tags = _merge_tags(
            raw.get("tags"),
            world_zone.get("population_tags"),
            [raw.get("node_type"), world_zone.get("zone_archetype"), raw.get("landmark_profile")],
            flags.get("context_tags"),
            _rift_tags(flags),
            anchor.get("tags"),
        )
        return MonsterLocationContext(
            loc_id=str(raw.get("loc_id") or loc_id),
            zone_id=str(world_zone.get("id") or raw.get("zone_id") or ""),
            biome_id=biome_id,
            tier=tier,
            danger=_to_float(anchor.get("threat", flags.get("threat", 0.0))),
            tags=tags,
            raw_location=dict(raw),
        )


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _merge_tags(*values: Any) -> list[str]:
    tags: list[str] = []
    for value in values:
        if isinstance(value, list):
            tags.extend(str(item) for item in value if item)
    return list(dict.fromkeys(tags))


def _rift_tags(flags: dict[str, Any]) -> list[str]:
    rift_profile = flags.get("rift_profile")
    if not isinstance(rift_profile, dict):
        return []
    tags = [str(tag) for tag in rift_profile.get("context_tags", []) if tag]
    for key in ("id", "family_id"):
        if rift_profile.get(key):
            tags.append(str(rift_profile[key]))
    return tags


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    try:
        return max(0.0, float(value or 0.0))
    except (TypeError, ValueError):
        return 0.0

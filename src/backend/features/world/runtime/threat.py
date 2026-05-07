from __future__ import annotations

from dataclasses import dataclass
from operator import itemgetter

from src.backend.features.world.runtime.config import (
    ANCHOR_ANOMALIES,
    ANCHORS,
    HUB_CENTER,
    HYBRID_TAGS,
    INFLUENCE_TAGS,
    PORTAL_PARAMS,
)


@dataclass(frozen=True)
class AnchorInfluence:
    x: int
    y: int
    threat: float
    tier: int
    dominant_anchor: str | None
    anomaly_id: str | None
    tags: list[str]
    is_inside_city_shield: bool


class ThreatService:
    TYPE_MAP = {
        "north_prime": "ice",
        "south_prime": "fire",
        "west_prime": "gravity",
        "east_prime": "bio",
    }
    CITY_RADIUS = 7

    @classmethod
    def describe(cls, x: int, y: int) -> AnchorInfluence:
        threat = cls.calculate_threat(x, y)
        tier = cls.get_tier_from_threat(threat)
        dominant_anchor = cls.get_dominant_anchor_type(x, y)
        return AnchorInfluence(
            x=x,
            y=y,
            threat=threat,
            tier=tier,
            dominant_anchor=dominant_anchor,
            anomaly_id=ANCHOR_ANOMALIES.get(dominant_anchor or ""),
            tags=cls.get_narrative_tags(x, y),
            is_inside_city_shield=cls._is_inside_city(x, y),
        )

    @classmethod
    def calculate_threat(cls, x: int, y: int) -> float:
        dist_hub = cls._get_dist(x, y, HUB_CENTER["x"], HUB_CENTER["y"])
        stability = PORTAL_PARAMS["power"] / (1 + dist_hub * PORTAL_PARAMS["falloff"])

        danger = 0.0
        for anchor in ANCHORS:
            dist = cls._get_dist(x, y, anchor["x"], anchor["y"])
            danger += anchor["power"] / (1 + dist * anchor["falloff"])

        if dist_hub <= cls.CITY_RADIUS:
            danger *= 0.25

        return max(0.0, min(1.0, danger - stability))

    @staticmethod
    def get_tier_from_threat(threat: float) -> int:
        if threat < 0.05:
            return 0
        if threat < 0.20:
            return 1
        if threat < 0.35:
            return 2
        if threat < 0.55:
            return 3
        if threat < 0.75:
            return 4
        if threat < 0.90:
            return 5
        if threat < 0.98:
            return 6
        return 7

    @classmethod
    def get_dominant_anchor_type(cls, x: int, y: int) -> str | None:
        influences = cls._anchor_influences(x, y, shield_modifier=1.0)
        return influences[0]["type"] if influences else None

    @classmethod
    def get_narrative_tags(cls, x: int, y: int) -> list[str]:
        threat_val = cls.calculate_threat(x, y)
        current_tier = cls.get_tier_from_threat(threat_val)
        is_inside_city = cls._is_inside_city(x, y)

        shield_modifier = cls._shield_modifier(x, y)
        if shield_modifier == 0.0:
            return []

        influences = cls._anchor_influences(x, y, shield_modifier=shield_modifier)
        threshold = 0.1 if is_inside_city else 0.05
        influences = [influence for influence in influences if influence["val"] > threshold]
        if not influences:
            return []

        active_tags: list[str] = []
        primary = influences[0]
        effective_tier = 1 if is_inside_city else current_tier
        active_tags.extend(cls._get_gradient_tags(primary["type"], effective_tier) or primary["tags"])

        if not is_inside_city:
            secondary = influences[1] if len(influences) > 1 else None
            if secondary and secondary["val"] > 0.15 and secondary["val"] > (primary["val"] * 0.7):
                secondary_tier = max(0, current_tier - 2)
                active_tags.extend(cls._get_gradient_tags(secondary["type"], secondary_tier) or secondary["tags"])

                key1 = cls.TYPE_MAP.get(primary["type"])
                key2 = cls.TYPE_MAP.get(secondary["type"])
                if key1 and key2:
                    active_tags.extend(HYBRID_TAGS.get(frozenset([key1, key2]), []))

        return list(dict.fromkeys(active_tags))

    @classmethod
    def _anchor_influences(cls, x: int, y: int, *, shield_modifier: float) -> list[dict]:
        influences = []
        for anchor in ANCHORS:
            dist = cls._get_dist(x, y, anchor["x"], anchor["y"])
            raw_influence = anchor["power"] / (1 + dist * anchor["falloff"])
            influences.append(
                {
                    "tags": anchor["narrative_tags"],
                    "val": raw_influence * shield_modifier,
                    "type": anchor.get("type", "unknown"),
                }
            )
        influences.sort(key=itemgetter("val"), reverse=True)
        return influences

    @classmethod
    def _shield_modifier(cls, x: int, y: int) -> float:
        dist_hub = cls._get_dist(x, y, HUB_CENTER["x"], HUB_CENTER["y"])
        if dist_hub <= cls.CITY_RADIUS:
            return 0.0 if dist_hub <= 4 else 0.2
        distance_from_wall = dist_hub - cls.CITY_RADIUS
        return distance_from_wall / 10.0 if distance_from_wall < 10 else 1.0

    @classmethod
    def _get_gradient_tags(cls, anchor_type: str, tier: int) -> list[str] | None:
        gradient_key = cls.TYPE_MAP.get(anchor_type)
        if not gradient_key:
            return None

        for (min_t, max_t), tags in INFLUENCE_TAGS.get(gradient_key, {}).items():
            if min_t <= tier <= max_t:
                return tags
        return None

    @classmethod
    def _is_inside_city(cls, x: int, y: int) -> bool:
        return cls._get_dist(x, y, HUB_CENTER["x"], HUB_CENTER["y"]) <= cls.CITY_RADIUS

    @staticmethod
    def _get_dist(x1: int, y1: int, x2: int, y2: int) -> float:
        return float(max(abs(x1 - x2), abs(y1 - y2)))

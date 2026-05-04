from __future__ import annotations

from operator import itemgetter

from typing import Any, Literal, TypedDict
from src.backend.features.world.runtime.config import ANCHORS, HUB_CENTER, PORTAL_PARAMS
from src.backend.features.world.runtime.threat import ThreatService
from src.shared.schemas.world_theme import WorldThemeDTO


class AnchorInfluence(TypedDict):
    type: str
    value: float


class WorldThemeService:
    ANCHOR_COLORS = {
        "north_prime": (125, 220, 255),
        "south_prime": (255, 106, 61),
        "west_prime": (143, 124, 255),
        "east_prime": (102, 209, 122),
    }
    NEUTRAL = (255, 170, 0)

    @classmethod
    def build(cls, x: int, y: int, *, loc_id: str | None = None) -> WorldThemeDTO:
        influences = cls._raw_anchor_influences(x, y)
        total_anchor = sum(item["value"] for item in influences) or 1.0
        weights: dict[str, float] = {
            item["type"]: round(item["value"] / total_anchor, 4) for item in influences
        }

        portal_power = cls._portal_power(x, y)
        shield_ratio = portal_power / (portal_power + total_anchor)
        threat = ThreatService.describe(x, y)
        shield_modifier = ThreatService._shield_modifier(x, y)
        tier_factor = threat.tier / 7.0
        intensity = cls._clamp(
            (1.0 - shield_ratio) * (0.18 + tier_factor * 0.82) * shield_modifier
        )
        if threat.is_inside_city_shield and threat.tier == 0:
            intensity = min(intensity, 0.08)

        mixed = cls._mix_anchor_colors(weights)
        accent_rgb = cls._lerp_rgb(cls.NEUTRAL, mixed, intensity)
        accent = cls._hex(accent_rgb)

        top = influences[0] if influences else None
        second = influences[1] if len(influences) > 1 else None

        mode: Literal["safe", "anchor", "hybrid"] = "safe"
        if intensity >= 0.12:
            if top and second and second["value"] >= top["value"] * 0.78:
                mode = "hybrid"
            else:
                mode = "anchor"

        dto = WorldThemeDTO(
            loc_id=loc_id,
            mode=mode,
            dominant_anchor=top["type"] if top else None,
            intensity=round(intensity, 4),
            weights=weights,
            accent=accent,
            accent_dim=cls._rgba(accent_rgb, 0.4),
            accent_soft=cls._rgba(accent_rgb, 0.08 + intensity * 0.08),
            accent_border=cls._rgba(accent_rgb, 0.18 + intensity * 0.18),
            accent_glow=cls._rgba(accent_rgb, 0.24 + intensity * 0.28),
            glass=cls._rgba((10, 10, 12), 0.56 + intensity * 0.08),
        )
        dto.css_vars = {
            "--world-accent": dto.accent,
            "--world-accent-dim": dto.accent_dim,
            "--world-accent-soft": dto.accent_soft,
            "--world-accent-border": dto.accent_border,
            "--world-accent-glow": dto.accent_glow,
            "--world-glass": dto.glass,
            "--world-intensity": str(dto.intensity),
        }
        return dto

    @classmethod
    def _raw_anchor_influences(cls, x: int, y: int) -> list[AnchorInfluence]:
        influences: list[AnchorInfluence] = []
        for anchor in ANCHORS:
            dist = ThreatService._get_dist(x, y, anchor["x"], anchor["y"])
            influences.append(
                {
                    "type": str(anchor.get("type", "unknown")),
                    "value": float(anchor["power"] / (1 + dist * anchor["falloff"])),
                }
            )
        influences.sort(key=itemgetter("value"), reverse=True)
        return influences

    @classmethod
    def _portal_power(cls, x: int, y: int) -> float:
        dist_hub = ThreatService._get_dist(x, y, HUB_CENTER["x"], HUB_CENTER["y"])
        return PORTAL_PARAMS["power"] / (1 + dist_hub * PORTAL_PARAMS["falloff"])

    @classmethod
    def _mix_anchor_colors(cls, weights: dict[str, float]) -> tuple[int, int, int]:
        rgb = [0.0, 0.0, 0.0]
        for anchor_type, weight in weights.items():
            color = cls.ANCHOR_COLORS.get(anchor_type, cls.NEUTRAL)
            rgb[0] += color[0] * weight
            rgb[1] += color[1] * weight
            rgb[2] += color[2] * weight
        result = tuple(round(channel) for channel in rgb)
        assert len(result) == 3
        return (result[0], result[1], result[2])

    @staticmethod
    def _lerp_rgb(
        a: tuple[int, int, int], b: tuple[int, int, int], t: float
    ) -> tuple[int, int, int]:
        result = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
        assert len(result) == 3
        return (result[0], result[1], result[2])

    @staticmethod
    def _hex(rgb: tuple[int, int, int]) -> str:
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    @staticmethod
    def _rgba(rgb: tuple[int, int, int], alpha: float) -> str:
        return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {WorldThemeService._clamp(alpha):.3f})"

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

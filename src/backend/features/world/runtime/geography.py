from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from src.backend.features.world.runtime.config import HUB_CENTER, REGION_SIZE


@dataclass(frozen=True)
class BiomeField:
    biome_id: str
    x: int
    y: int
    radius: float
    weight: float


class ZoneGeography(TypedDict):
    primary_biome: str
    secondary_biomes: list[str]
    biome_mix: dict[str, float]


class WorldGeographyService:
    """Selects the base geographic biome before anomaly influence is applied."""

    CITY_RADIUS = 7
    FIELDS = (
        BiomeField("mountains", 12, 8, 36.0, 1.35),
        BiomeField("forest", 26, 24, 42.0, 1.2),
        BiomeField("hills", 38, 34, 30.0, 0.75),
        BiomeField("grassland", 52, 52, 40.0, 1.0),
        BiomeField("meadow", 44, 60, 28.0, 0.78),
        BiomeField("badlands", 85, 28, 42.0, 1.15),
        BiomeField("canyon", 93, 48, 34.0, 1.0),
        BiomeField("savanna", 75, 72, 36.0, 0.86),
        BiomeField("swamp", 22, 82, 38.0, 1.16),
        BiomeField("marsh", 55, 90, 34.0, 1.0),
        BiomeField("highlands", 70, 18, 30.0, 0.72),
        BiomeField("jungle", 91, 86, 34.0, 0.94),
        BiomeField("wasteland", 70, 45, 25.0, 0.58),
    )

    @classmethod
    def describe_zone(cls, center_x: int, center_y: int) -> ZoneGeography:
        primary = cls.get_biome_id(center_x, center_y)
        ranked = cls._ranked_fields(center_x, center_y)
        secondary = [field.biome_id for field, score in ranked if field.biome_id != primary and score >= 0.22][:2]
        return {
            "primary_biome": primary,
            "secondary_biomes": secondary,
            "biome_mix": cls._biome_mix(ranked, primary),
        }

    @classmethod
    def get_biome_id(cls, x: int, y: int) -> str:
        if cls._is_inside_old_capital(x, y):
            return "city_ruins"

        ranked = cls._ranked_fields(x, y)
        if not ranked:
            return "wasteland"
        return ranked[0][0].biome_id

    @classmethod
    def _ranked_fields(cls, x: int, y: int) -> list[tuple[BiomeField, float]]:
        scores = [(field, cls._field_score(field, x, y)) for field in cls.FIELDS]
        return sorted((item for item in scores if item[1] > 0), key=lambda item: item[1], reverse=True)

    @classmethod
    def _biome_mix(cls, ranked: list[tuple[BiomeField, float]], primary: str) -> dict[str, float]:
        top = ranked[:3]
        total = sum(score for _, score in top)
        if total <= 0:
            return {primary: 1.0}
        return {field.biome_id: round(score / total, 3) for field, score in top}

    @staticmethod
    def _field_score(field: BiomeField, x: int, y: int) -> float:
        dist = max(abs(x - field.x), abs(y - field.y))
        falloff = max(0.0, 1.0 - (dist / field.radius))
        variation = WorldGeographyService._variation(x, y, field.biome_id)
        return falloff * field.weight + variation

    @staticmethod
    def _variation(x: int, y: int, key: str) -> float:
        raw = (x * 73856093) ^ (y * 19349663) ^ (sum(ord(char) for char in key) * 83492791)
        return ((raw & 0xFFFF) / 0xFFFF - 0.5) * 0.08

    @classmethod
    def _is_inside_old_capital(cls, x: int, y: int) -> bool:
        return (
            abs(x - HUB_CENTER["x"]) <= cls.CITY_RADIUS
            and abs(y - HUB_CENTER["y"]) <= cls.CITY_RADIUS
            and x // REGION_SIZE == HUB_CENTER["x"] // REGION_SIZE
            and y // REGION_SIZE == HUB_CENTER["y"] // REGION_SIZE
        )

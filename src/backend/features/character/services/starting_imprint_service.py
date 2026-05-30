from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping
from dataclasses import dataclass

from src.backend.features.character.resources.starting_imprints import (
    ATTRIBUTE_KEYS,
    DEFAULT_ATTRIBUTE_TAIL_ORDER,
    DEFAULT_STARTING_IMPRINT_KEY,
    STARTING_ARMOR_PACKS,
    STARTING_ATTRIBUTE_LADDER,
    STARTING_COMBAT_STYLES,
    STARTING_IMPRINTS,
    STARTING_UTILITY_PACKS,
    StartingImprintDefinition,
    StartingLoadoutPack,
)


@dataclass(frozen=True, slots=True)
class StartingImprintBuild:
    imprint_key: str
    title: str
    attributes: dict[str, int]
    skill_xp: dict[str, float]
    skill_keys: tuple[str, ...]
    item_base_ids: tuple[str, ...]
    primary_stats: tuple[str, ...]
    combat_style: str
    armor_pack: str
    utility_pack: str
    lore_tags: tuple[str, ...]
    description: str


class StartingImprintService:
    """Build future starter materialization payloads without mutating character state."""

    @staticmethod
    def available_keys() -> tuple[str, ...]:
        return tuple(STARTING_IMPRINTS)

    def build(self, imprint_key: str = DEFAULT_STARTING_IMPRINT_KEY) -> StartingImprintBuild:
        imprint = self.get_definition(imprint_key)
        combat = self._get_pack(STARTING_COMBAT_STYLES, imprint.combat_style, "combat_style")
        armor = self._get_pack(STARTING_ARMOR_PACKS, imprint.armor_pack, "armor_pack")
        utility = self._get_pack(STARTING_UTILITY_PACKS, imprint.utility_pack, "utility_pack")
        return StartingImprintBuild(
            imprint_key=imprint.imprint_key,
            title=imprint.title,
            attributes=self._build_attributes(imprint.primary_stats, seed=imprint.imprint_key),
            skill_xp=self._skill_xp(imprint.skill_xp),
            skill_keys=tuple(skill_key for skill_key, _ in imprint.skill_xp),
            item_base_ids=self._dedupe((*combat.item_base_ids, *armor.item_base_ids, *utility.item_base_ids)),
            primary_stats=imprint.primary_stats,
            combat_style=imprint.combat_style,
            armor_pack=imprint.armor_pack,
            utility_pack=imprint.utility_pack,
            lore_tags=imprint.lore_tags,
            description=imprint.description,
        )

    def build_random(self, *, seed: str | None = None) -> StartingImprintBuild:
        imprint_keys = tuple(STARTING_IMPRINTS)
        if not imprint_keys:
            raise ValueError("No starting imprints are defined")
        rng = random.Random(seed) if seed is not None else random.SystemRandom()
        return self.build(rng.choice(imprint_keys))

    def build_for_weights(self, weights: Mapping[str, float | int] | None) -> StartingImprintBuild:
        return self.build(self.select_for_weights(weights).imprint_key)

    def select_for_weights(self, weights: Mapping[str, float | int] | None) -> StartingImprintDefinition:
        if not weights:
            return self.get_definition(DEFAULT_STARTING_IMPRINT_KEY)

        normalized = {key.removeprefix("w_"): float(value) for key, value in weights.items()}
        best_imprint: StartingImprintDefinition | None = None
        best_score: tuple[float, int] | None = None
        for index, imprint in enumerate(STARTING_IMPRINTS.values()):
            score = sum(
                normalized.get(stat, 0.0) * self._primary_weight(position)
                for position, stat in enumerate(imprint.primary_stats)
            )
            ranked_score = (score, -index)
            if best_score is None or ranked_score > best_score:
                best_score = ranked_score
                best_imprint = imprint
        return best_imprint or self.get_definition(DEFAULT_STARTING_IMPRINT_KEY)

    @staticmethod
    def get_definition(imprint_key: str) -> StartingImprintDefinition:
        try:
            return STARTING_IMPRINTS[imprint_key]
        except KeyError as exc:
            raise ValueError(f"Unknown starting imprint: {imprint_key}") from exc

    @staticmethod
    def _build_attributes(primary_stats: tuple[str, ...], *, seed: str) -> dict[str, int]:
        order = StartingImprintService._attribute_order(primary_stats, seed=seed)
        return dict(zip(order, STARTING_ATTRIBUTE_LADDER, strict=True))

    @staticmethod
    def _attribute_order(primary_stats: tuple[str, ...], *, seed: str) -> tuple[str, ...]:
        unknown = [stat for stat in primary_stats if stat not in ATTRIBUTE_KEYS]
        if unknown:
            raise ValueError(f"Unknown starting imprint attributes: {unknown}")

        order = list(StartingImprintService._dedupe(primary_stats))
        tail = [stat for stat in DEFAULT_ATTRIBUTE_TAIL_ORDER if stat not in order]
        StartingImprintService._stable_shuffle(tail, seed=seed)
        order.extend(tail)
        if set(order) != set(ATTRIBUTE_KEYS) or len(order) != len(ATTRIBUTE_KEYS):
            raise ValueError("Starting imprint attribute order does not cover the character attribute contract")
        return tuple(order)

    @staticmethod
    def _get_pack(packs: Mapping[str, StartingLoadoutPack], key: str, kind: str) -> StartingLoadoutPack:
        try:
            return packs[key]
        except KeyError as exc:
            raise ValueError(f"Unknown starting imprint {kind}: {key}") from exc

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value for value in values if value))

    @staticmethod
    def _skill_xp(values: tuple[tuple[str, float], ...]) -> dict[str, float]:
        skill_xp: dict[str, float] = {}
        for skill_key, xp in values:
            if not skill_key:
                continue
            skill_xp[skill_key] = round(float(xp), 4)
        return skill_xp

    @staticmethod
    def _stable_shuffle(values: list[str], *, seed: str) -> None:
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        random.Random(int.from_bytes(digest[:8], "big")).shuffle(values)

    @staticmethod
    def _primary_weight(position: int) -> float:
        return max(1.0, 5.0 - float(position))

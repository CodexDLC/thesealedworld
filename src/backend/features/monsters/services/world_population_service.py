from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.features.monsters.dto import MonsterGenerationContext
from src.backend.features.monsters.runtime.hashing import normalize_tags

if TYPE_CHECKING:
    from src.backend.features.monsters.services.encounter_monster_service import EncounterMonsterService
    from src.backend.infrastructure.world.models import WorldGrid

D4_STARTER_FAMILY_IDS = ("bandit_gang", "goblin_tribe", "rat_swarm", "wolf_pack")
D4_TIER1_START_CONTEXT_TAGS = ("d4_city_ruins", "d4_tier1_start_population", *D4_STARTER_FAMILY_IDS)
D4_TIER1_CONTEXT_TAGS = ("d4_city_ruins", "d4_corner_pressure", "d4_tier1_population", *D4_STARTER_FAMILY_IDS)


@dataclass(frozen=True, slots=True)
class MonsterPopulationResult:
    contexts: int
    clans: int


class WorldMonsterPopulationService:
    """Seeds generated monster clans for already active world nodes."""

    def __init__(self, encounter_service: EncounterMonsterService) -> None:
        self.encounter_service = encounter_service

    async def ensure_population_for_nodes(self, nodes: list[WorldGrid]) -> MonsterPopulationResult:
        contexts = self._build_unique_contexts(nodes)
        clans_count = 0

        for context in contexts:
            for family_id in self.encounter_service.get_available_family_ids(context):
                await self.encounter_service.ensure_clan_for_context(context, family_id)
                clans_count += 1

        log.bind(context_count=len(contexts), clan_count=clans_count).info("MonsterWorldPopulationEnsured")
        return MonsterPopulationResult(contexts=len(contexts), clans=clans_count)

    def _build_unique_contexts(self, nodes: list[WorldGrid]) -> list[MonsterGenerationContext]:
        contexts: dict[tuple[int, str, tuple[str, ...]], MonsterGenerationContext] = {}

        for node in nodes:
            flags = node.flags if isinstance(node.flags, dict) else {}
            if bool(flags.get("is_safe_zone")):
                continue

            zone = getattr(node, "zone", None)
            zone_flags = getattr(zone, "flags", None)
            if isinstance(zone_flags, dict) and bool(zone_flags.get("is_safe_zone")):
                continue
            if bool(flags.get("is_rift")) or flags.get("rift_profile"):
                continue

            biome_id = str(getattr(zone, "biome_id", None) or "wasteland")
            tier = self._resolve_tier(node, flags, zone)
            tags = self._collect_tags(node, flags, zone)

            d4_context = self._build_d4_context(node, flags, zone, biome_id, tags)
            if d4_context is not None:
                key = (d4_context.tier, d4_context.biome_id, tuple(normalize_tags(d4_context.tags)))
                contexts.setdefault(key, d4_context)
                continue

            key = (tier, biome_id, tuple(normalize_tags(tags)))
            contexts.setdefault(
                key,
                MonsterGenerationContext(
                    zone_id=str(getattr(zone, "id", None) or node.zone_id),
                    biome_id=biome_id,
                    tier=tier,
                    tags=tags,
                    difficulty="mid",
                    context_meta={"rift_profile": flags.get("rift_profile")} if flags.get("rift_profile") else {},
                ),
            )

        return list(contexts.values())

    @staticmethod
    def _build_d4_context(
        node: WorldGrid,
        flags: dict[str, Any],
        zone: Any,
        biome_id: str,
        tags: list[str],
    ) -> MonsterGenerationContext | None:
        zone_id = str(getattr(zone, "id", None) or node.zone_id)
        if biome_id != "city_ruins" or not zone_id.startswith("D4_"):
            return None

        if "d4_corner_pressure" in set(tags):
            return MonsterGenerationContext(
                zone_id="D4_tier1_corner_pressure",
                biome_id=biome_id,
                tier=1,
                tags=list(D4_TIER1_CONTEXT_TAGS),
                difficulty="mid",
            )

        return MonsterGenerationContext(
            zone_id="D4_tier1_start",
            biome_id=biome_id,
            tier=1,
            tags=list(D4_TIER1_START_CONTEXT_TAGS),
            difficulty="mid",
        )

    @staticmethod
    def _resolve_tier(node: WorldGrid, flags: dict[str, Any], zone: Any) -> int:
        candidates = [getattr(zone, "tier", 0) or 0, flags.get("threat_tier", 0)]
        return max(1, min(7, max(_to_int(value) for value in candidates)))

    @staticmethod
    def _collect_tags(node: WorldGrid, flags: dict[str, Any], zone: Any) -> list[str]:
        content = node.content if isinstance(node.content, dict) else {}
        tags: list[str] = [str(tag) for tag in content.get("environment_tags", [])]
        zone_population_tags = getattr(zone, "population_tags", None)
        if isinstance(zone_population_tags, list):
            tags.extend(str(tag) for tag in zone_population_tags if tag)
        for value in (getattr(zone, "zone_archetype", None), getattr(zone, "landmark_profile", None)):
            if value:
                tags.append(str(value))
        tags.extend(str(tag) for tag in flags.get("context_tags", []) if tag)
        rift_profile = flags.get("rift_profile")
        if isinstance(rift_profile, dict):
            tags.extend(str(tag) for tag in rift_profile.get("context_tags", []) if tag)
            for key in ("id", "family_id"):
                if rift_profile.get(key):
                    tags.append(str(rift_profile[key]))
        anchor_influence = flags.get("anchor_influence")
        if isinstance(anchor_influence, dict):
            tags.extend(str(tag) for tag in anchor_influence.get("tags", []))
        return list(dict.fromkeys(tags))


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

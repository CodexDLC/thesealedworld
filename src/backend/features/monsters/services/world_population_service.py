from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.monsters.dto import MonsterGenerationContext
from src.backend.features.monsters.runtime.hashing import normalize_tags

if TYPE_CHECKING:
    from src.backend.features.monsters.services.encounter_monster_service import EncounterMonsterService
    from src.backend.infrastructure.world.models import WorldGrid

log = logging.getLogger(__name__)


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

        log.info("Monster world population ensured: contexts=%s clans=%s", len(contexts), clans_count)
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

            biome_id = str(getattr(zone, "biome_id", None) or "wasteland")
            tier = self._resolve_tier(node, flags, zone)
            tags = self._collect_tags(node, flags)
            key = (tier, biome_id, tuple(normalize_tags(tags)))
            contexts.setdefault(
                key,
                MonsterGenerationContext(
                    zone_id=str(getattr(zone, "id", None) or node.zone_id),
                    biome_id=biome_id,
                    tier=tier,
                    tags=tags,
                    difficulty="mid",
                ),
            )

        return list(contexts.values())

    @staticmethod
    def _resolve_tier(node: WorldGrid, flags: dict[str, Any], zone: Any) -> int:
        candidates = [getattr(zone, "tier", 0) or 0, flags.get("threat_tier", 0)]
        anchor_influence = flags.get("anchor_influence")
        if isinstance(anchor_influence, dict):
            candidates.append(anchor_influence.get("tier", 0))
        return max(0, min(7, max(_to_int(value) for value in candidates)))

    @staticmethod
    def _collect_tags(node: WorldGrid, flags: dict[str, Any]) -> list[str]:
        content = node.content if isinstance(node.content, dict) else {}
        tags: list[str] = [str(tag) for tag in content.get("environment_tags", [])]
        anchor_influence = flags.get("anchor_influence")
        if isinstance(anchor_influence, dict):
            tags.extend(str(tag) for tag in anchor_influence.get("tags", []))
        return list(dict.fromkeys(tags))


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

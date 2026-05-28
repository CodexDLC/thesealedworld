from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.features.monsters.dto import MonsterGenerationContext
from src.backend.features.rift.runtime.generation import build_population_context

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.monsters.services.encounter_monster_service import EncounterMonsterService
    from src.backend.features.rift.resources.loader import RiftResourceLoader


@dataclass(frozen=True, slots=True)
class RiftPopulationBootstrapResult:
    rifts: int
    family_slots: int
    clans: int
    bindings: dict[str, dict[str, dict[str, Any]]]


class RiftPopulationBootstrapService:
    """Creates generated monster clans for authored rift family slots."""

    def __init__(
        self,
        *,
        loader: RiftResourceLoader,
        encounter_service: EncounterMonsterService,
    ) -> None:
        self.loader = loader
        self.encounter_service = encounter_service

    async def ensure_static_population(
        self, setting_keys: Sequence[str] | None = None
    ) -> RiftPopulationBootstrapResult:
        keys = list(setting_keys or self.loader.list_setting_keys())
        rifts_count = 0
        slots_count = 0
        clans_count = 0
        bindings: dict[str, dict[str, dict[str, Any]]] = {}

        for setting_key in keys:
            setting = self.loader.load_setting(setting_key)
            population = build_population_context(setting)
            family_slots = population.get("family_slots")
            if not isinstance(family_slots, list) or not family_slots:
                continue

            rifts_count += 1
            for raw_slot in family_slots:
                if not isinstance(raw_slot, dict):
                    continue
                slots_count += 1
                slot_id = str(raw_slot.get("slot_id") or "").strip()
                family_id = str(raw_slot.get("family_id") or raw_slot.get("prototype_family_key") or "").strip()
                context_hash = str(raw_slot.get("context_hash") or "").strip()
                if not family_id or not context_hash:
                    continue

                context = _build_slot_generation_context(population, raw_slot)
                tags = _build_slot_tags(population, raw_slot)
                clan = await self.encounter_service.ensure_clan_for_precomputed_context_hash(
                    context,
                    family_id,
                    context_hash=context_hash,
                    normalized_tags=tags,
                )
                bindings.setdefault(setting_key, {})[slot_id] = {
                    "slot_id": slot_id,
                    "family_id": family_id,
                    "clan_id": str(clan.id),
                    "context_hash": context_hash,
                    "unique_hash": clan.unique_hash,
                    "source": "rift_static_bootstrap",
                }
                clans_count += 1

        log.bind(rift_count=rifts_count, slot_count=slots_count, clan_count=clans_count).info(
            "RiftStaticPopulationEnsured"
        )
        return RiftPopulationBootstrapResult(
            rifts=rifts_count,
            family_slots=slots_count,
            clans=clans_count,
            bindings=bindings,
        )


def _build_slot_generation_context(population: dict[str, Any], slot: dict[str, Any]) -> MonsterGenerationContext:
    setting_key = str(population.get("setting_key") or "rift")
    slot_id = str(slot.get("slot_id") or "slot")
    return MonsterGenerationContext(
        zone_id=f"rift:{setting_key}:{slot_id}",
        biome_id=str(population.get("biome_id") or "wasteland"),
        tier=max(1, int(population.get("tier") or 1)),
        tags=_build_slot_tags(population, slot),
        difficulty="mid",
        context_meta={
            "rift_population": {
                "source": str(population.get("source") or "rift_static"),
                "setting_key": setting_key,
                "slot_id": slot_id,
                "role": str(slot.get("role") or ""),
                "family_profile_key": str(slot.get("family_profile_key") or ""),
                "archetype": str(slot.get("archetype") or ""),
                "hash_strategy": str(population.get("hash_strategy") or "rift_context_v1"),
            }
        },
    )


def _build_slot_tags(population: dict[str, Any], slot: dict[str, Any]) -> list[str]:
    return _merge_tags(
        population.get("tags"),
        population.get("selection_tags"),
        slot.get("selection_tags"),
        [
            slot.get("slot_id"),
            slot.get("role"),
            slot.get("family_profile_key"),
            slot.get("archetype"),
            slot.get("prototype_family_key"),
        ],
    )


def _merge_tags(*sources: Any) -> list[str]:
    tags: list[str] = []
    for source in sources:
        values = source if isinstance(source, list) else [source]
        for value in values:
            text = str(value or "").strip()
            if text and text not in tags:
                tags.append(text)
    return tags

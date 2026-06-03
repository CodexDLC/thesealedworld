from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.features.monsters.dto import MonsterGenerationContext
from src.backend.features.monsters.runtime.hashing import (
    MonsterHashContext,
    compute_monster_context_hash,
    normalized_monster_hash_tags,
)
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
    pruned_clans: int
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
        pruned_clans_count = 0
        bindings: dict[str, dict[str, dict[str, Any]]] = {}

        for setting_key in keys:
            setting = self.loader.load_setting(setting_key)
            population = build_population_context(setting)
            family_slots = population.get("family_slots")
            if not isinstance(family_slots, list) or not family_slots:
                continue

            rifts_count += 1
            expected_zone_contexts: dict[str, set[tuple[str, str]]] = {}
            for raw_slot in family_slots:
                if not isinstance(raw_slot, dict):
                    continue
                slots_count += 1
                slot_id = str(raw_slot.get("slot_id") or "").strip()
                family_id = str(raw_slot.get("family_id") or raw_slot.get("prototype_family_key") or "").strip()
                hash_context = _slot_hash_context(raw_slot)
                if not family_id or hash_context is None:
                    continue

                context_hash = compute_monster_context_hash(hash_context)
                expected_zone_contexts.setdefault(f"rift:{setting_key}:{slot_id}", set()).add((family_id, context_hash))
                tags = normalized_monster_hash_tags(hash_context)
                context = _build_slot_generation_context(population, raw_slot, hash_context=hash_context, tags=tags)
                clan = await self.encounter_service.ensure_clan_for_hash_context(
                    context,
                    family_id,
                    hash_context=hash_context,
                )
                bindings.setdefault(setting_key, {})[slot_id] = {
                    "slot_id": slot_id,
                    "family_id": family_id,
                    "context_hash": context_hash,
                    "unique_hash": clan.unique_hash,
                    "hash_context": _hash_context_payload(hash_context),
                    "normalized_tags": tags,
                    "source": "rift_static_bootstrap",
                }
                clans_count += 1

            if expected_zone_contexts:
                pruned_clans_count += await self.encounter_service.prune_generated_clans_for_zone_contexts(
                    expected_zone_contexts
                )

        log.bind(
            rift_count=rifts_count,
            slot_count=slots_count,
            clan_count=clans_count,
            pruned_clan_count=pruned_clans_count,
        ).info("RiftStaticPopulationEnsured")
        return RiftPopulationBootstrapResult(
            rifts=rifts_count,
            family_slots=slots_count,
            clans=clans_count,
            pruned_clans=pruned_clans_count,
            bindings=bindings,
        )


def _build_slot_generation_context(
    population: dict[str, Any],
    slot: dict[str, Any],
    *,
    hash_context: MonsterHashContext,
    tags: list[str],
) -> MonsterGenerationContext:
    setting_key = str(population.get("setting_key") or "rift")
    slot_id = str(slot.get("slot_id") or "slot")
    return MonsterGenerationContext(
        zone_id=f"rift:{setting_key}:{slot_id}",
        biome_id=hash_context.biome_id,
        tier=max(1, int(hash_context.tier)),
        tags=tags,
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


def _slot_hash_context(slot: dict[str, Any]) -> MonsterHashContext | None:
    raw = slot.get("hash_context")
    if not isinstance(raw, dict):
        return None
    source = str(raw.get("source") or "")
    if source != "rift":
        return None
    context_key = str(raw.get("context_key") or "").strip()
    biome_id = str(raw.get("biome_id") or "").strip()
    if not context_key or not biome_id:
        return None
    return MonsterHashContext(
        source="rift",
        context_key=context_key,
        biome_id=biome_id,
        tier=max(1, int(raw.get("tier") or 1)),
        tags=tuple(_merge_tags(raw.get("tags"))),
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


def _hash_context_payload(context: MonsterHashContext) -> dict[str, Any]:
    return {
        "source": context.source,
        "context_key": context.context_key,
        "biome_id": context.biome_id,
        "tier": context.tier,
        "tags": list(context.tags),
    }

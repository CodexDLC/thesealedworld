from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from src.backend.features.monsters.dto import GeneratedClan, MonsterGenerationContext
from src.backend.features.monsters.runtime.hashing import (
    MonsterHashContext,
    compute_monster_context_hash,
    compute_unique_clan_hash,
)
from src.backend.features.rift.resources.loader import RiftResourceLoader
from src.backend.features.rift.services.population_bootstrap import RiftPopulationBootstrapService


@dataclass(slots=True)
class RiftClanRequest:
    context: MonsterGenerationContext
    family_id: str
    hash_context: MonsterHashContext


class FakeEncounterService:
    def __init__(self) -> None:
        self.requests: list[RiftClanRequest] = []
        self.prune_requests: list[dict[str, set[tuple[str, str]]]] = []

    async def ensure_clan_for_hash_context(
        self,
        context: MonsterGenerationContext,
        family_id: str,
        *,
        hash_context: MonsterHashContext,
    ) -> GeneratedClan:
        context_hash = compute_monster_context_hash(hash_context)
        self.requests.append(
            RiftClanRequest(
                context=context,
                family_id=family_id,
                hash_context=hash_context,
            )
        )
        return GeneratedClan(
            id=uuid.uuid4(),
            family_id=family_id,
            tier=context.tier,
            zone_id=context.zone_id,
            context_hash=context_hash,
            unique_hash=compute_unique_clan_hash(family_id, context_hash),
            raw_tags={},
            flavor_content={},
            name_ru=family_id,
            description=family_id,
        )

    async def prune_generated_clans_for_zone_contexts(self, expected: dict[str, set[tuple[str, str]]]) -> int:
        self.prune_requests.append(expected)
        return 3


@pytest.mark.unit
async def test_rift_population_bootstrap_orders_static_family_slots_with_rift_hashes() -> None:
    encounter = FakeEncounterService()
    service = RiftPopulationBootstrapService(
        loader=RiftResourceLoader(),
        encounter_service=encounter,  # type: ignore[arg-type]
    )

    result = await service.ensure_static_population(["starter_rift"])

    assert result.rifts == 1
    assert result.family_slots == 2
    assert result.clans == 2
    assert result.pruned_clans == 3
    assert set(result.bindings["starter_rift"]) == {"primary", "secondary"}
    assert result.bindings["starter_rift"]["primary"]["family_id"] == "goblin_tribe"
    assert "clan_id" not in result.bindings["starter_rift"]["primary"]
    assert result.bindings["starter_rift"]["primary"]["context_hash"] == compute_monster_context_hash(
        encounter.requests[0].hash_context
    )
    assert result.bindings["starter_rift"]["primary"]["unique_hash"] == compute_unique_clan_hash(
        "goblin_tribe",
        compute_monster_context_hash(encounter.requests[0].hash_context),
    )
    assert [(request.context.zone_id, request.family_id) for request in encounter.requests] == [
        ("rift:starter_rift:primary", "goblin_tribe"),
        ("rift:starter_rift:secondary", "rat_swarm"),
    ]
    assert compute_monster_context_hash(encounter.requests[0].hash_context) != compute_monster_context_hash(
        encounter.requests[1].hash_context
    )
    assert "starter_rift" in encounter.requests[0].hash_context.tags
    assert "camp_guard" in encounter.requests[0].hash_context.tags
    assert encounter.requests[0].context.context_meta["rift_population"]["slot_id"] == "primary"
    assert encounter.prune_requests == [
        {
            "rift:starter_rift:primary": {
                ("goblin_tribe", compute_monster_context_hash(encounter.requests[0].hash_context))
            },
            "rift:starter_rift:secondary": {
                ("rat_swarm", compute_monster_context_hash(encounter.requests[1].hash_context))
            },
        }
    ]

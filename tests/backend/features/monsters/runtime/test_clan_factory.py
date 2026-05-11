import pytest

from src.backend.features.monsters.dto.generation import MonsterGenerationContext
from src.backend.features.monsters.runtime.clan_factory import ClanFactory
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags


@pytest.mark.unit
async def test_factory_creates_clan_with_members_from_resource_data() -> None:
    context = MonsterGenerationContext(
        zone_id="D4_0_1",
        biome_id="forest",
        tier=1,
        tags=["mana_leak"],
        difficulty="mid",
    )
    tags = normalize_tags(context.tags)
    context_hash = compute_context_hash(context.tier, context.biome_id, tags)
    family_id = ClanFactory().select_family_id(context, context_hash)
    assert family_id is not None

    clan, members = await ClanFactory().build_clan_with_members(
        family_id=family_id,
        context=context,
        context_hash=context_hash,
        unique_hash=compute_unique_clan_hash(family_id, context_hash),
        normalized_tags=tags,
    )

    assert clan.zone_id == "D4_0_1"
    assert clan.context_hash == context_hash
    assert members
    assert all(member.clan_id == clan.id for member in members)
    assert all(member.scaled_base_stats for member in members)
    assert all(member.combat_seed.get("skills") for member in members)
    assert all(member.combat_seed.get("loadout") for member in members)


@pytest.mark.unit
async def test_factory_uses_neighbor_tier_variants_without_raising_scaling_tier() -> None:
    context = MonsterGenerationContext(
        zone_id="D4_0_1",
        biome_id="city_ruins",
        tier=1,
        tags=["mana_leak"],
        difficulty="mid",
    )
    tags = normalize_tags(context.tags)
    context_hash = compute_context_hash(context.tier, context.biome_id, tags)

    clan, members = await ClanFactory().build_clan_with_members(
        family_id="wolf_pack",
        context=context,
        context_hash=context_hash,
        unique_hash=compute_unique_clan_hash("wolf_pack", context_hash),
        normalized_tags=tags,
    )

    member_keys = {member.variant_key for member in members}
    assert {"cub", "runner", "pack_leader", "dire_wolf", "old_fang"}.issubset(member_keys)
    assert clan.tier == 1


class FakeMonsterTextAI:
    def __init__(self) -> None:
        self.payload = None

    async def generate_clan_flavor(self, payload):
        from src.backend.features.monsters.integrations.text_ai_client import (
            MonsterClanFlavorDTO,
            MonsterVariantFlavorDTO,
        )

        self.payload = payload
        return MonsterClanFlavorDTO(
            name_ru="Банда Ржавого Клинка",
            description="Бандиты, пропитанные холодом руин. Они не носят знамен, но узнают друг друга по ржавым меткам.",
            variants_flavor={
                key: MonsterVariantFlavorDTO(
                    name=f"Бродяга '{idx}'",
                    appearance="Оборванец с ледяной пылью на плаще.",
                    detected="Оборванец пятится к разбитой арке.",
                    ambush="Оборванец выскакивает из разбитой арки.",
                    idle="Оборванец перебирает чужие вещи у стены.",
                    encounter="Он выходит из разбитой арки.",
                    behavior="Держится ближе к темным проходам.",
                )
                for idx, key in enumerate(payload["units_to_name"], start=1)
            },
        )


@pytest.mark.unit
async def test_factory_uses_ai_flavor_for_clan_and_members() -> None:
    context = MonsterGenerationContext(
        zone_id="D4_0_1",
        biome_id="city_ruins",
        tier=1,
        tags=["frozen_dew", "cold_stone"],
        difficulty="mid",
    )
    tags = normalize_tags(context.tags)
    context_hash = compute_context_hash(context.tier, context.biome_id, tags)
    family_id = "bandit_gang"
    fake_ai = FakeMonsterTextAI()

    clan, members = await ClanFactory(text_ai=fake_ai).build_clan_with_members(
        family_id=family_id,
        context=context,
        context_hash=context_hash,
        unique_hash=compute_unique_clan_hash(family_id, context_hash),
        normalized_tags=tags,
    )

    assert fake_ai.payload["family_id"] == family_id
    assert fake_ai.payload["context_tags"] == tags
    assert fake_ai.payload["text_contract"]["member"] == [
        "name",
        "appearance",
        "detected",
        "ambush",
        "idle",
        "encounter",
        "behavior",
    ]
    assert clan.name_ru == "Банда Ржавого Клинка"
    assert clan.flavor_content["variants_flavor"]
    assert members[0].name_ru.startswith("Бродяга")
    assert members[0].description == "Оборванец с ледяной пылью на плаще."

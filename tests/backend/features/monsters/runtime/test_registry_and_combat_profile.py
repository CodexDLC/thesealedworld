import pytest

from src.backend.features.items.resources import get_base_by_id
from src.backend.features.monsters.dto.generation import MonsterGenerationContext
from src.backend.features.monsters.resources import get_family_config, get_starter_family_ids
from src.backend.features.monsters.runtime.clan_factory import ClanFactory
from src.backend.features.monsters.runtime.combat_profile import build_monster_combat_context, build_monster_vitals
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags


@pytest.mark.unit
def test_registry_loads_only_starter_families() -> None:
    assert get_starter_family_ids() == ("rat_swarm", "wolf_pack", "bandit_gang", "goblin_tribe")
    assert get_family_config("rat_swarm") is not None
    assert get_family_config("wolf_pack") is not None
    assert get_family_config("bandit_gang") is not None
    assert get_family_config("goblin_tribe") is not None
    assert get_family_config("dragon_brood") is None


@pytest.mark.unit
def test_monster_natural_equipment_is_registered_as_item_base() -> None:
    weapon = get_base_by_id("rat_bite_claws")
    armor = get_base_by_id("light_hide")

    assert weapon is not None
    assert weapon["slot"] == "main_hand"
    assert weapon["triggers"] == ["crit.bleed_on_crit"]
    assert armor is not None
    assert armor["slot"] == "chest_armor"


@pytest.mark.unit
def test_rat_beast_profile_builds_combat_ready_context() -> None:
    context = MonsterGenerationContext(zone_id="D4_0_1", biome_id="city_ruins", tier=1, tags=["mana_leak"])
    tags = normalize_tags(context.tags)
    context_hash = compute_context_hash(context.tier, context.biome_id, tags)
    clan, members = ClanFactory().build_clan_with_members(
        family_id="rat_swarm",
        context=context,
        context_hash=context_hash,
        unique_hash=compute_unique_clan_hash("rat_swarm", context_hash),
        normalized_tags=tags,
    )
    monster = members[0]
    monster.clan = clan

    combat = build_monster_combat_context(monster)
    vitals = build_monster_vitals(monster)

    assert combat["math_model"]["attributes"]["strength"]["base"] > 0
    assert combat["math_model"]["attributes"]["intellect"]["base"] >= 0
    assert combat["math_model"]["modifiers"]["main_hand_damage_base"]["source"]
    assert combat["loadout"]["layout"]["main_hand"] == "rat_bite_claws"
    assert combat["loadout"]["layout"]["chest_armor"] == "light_hide"
    assert combat["loadout"]["known_abilities"]
    assert combat["skills"]["skill_unarmed"] >= 20
    assert vitals["hp_current"] > 0


@pytest.mark.unit
def test_bandit_humanoid_loadout_resolves_into_modifiers_and_layout() -> None:
    context = MonsterGenerationContext(zone_id="D4_0_1", biome_id="city_ruins", tier=1, tags=["mana_leak"])
    tags = normalize_tags(context.tags)
    context_hash = compute_context_hash(context.tier, context.biome_id, tags)
    clan, members = ClanFactory().build_clan_with_members(
        family_id="bandit_gang",
        context=context,
        context_hash=context_hash,
        unique_hash=compute_unique_clan_hash("bandit_gang", context_hash),
        normalized_tags=tags,
    )
    monster = next(member for member in members if member.variant_key == "bandit_thug")
    monster.clan = clan

    combat = build_monster_combat_context(monster)

    assert combat["loadout"]["layout"]["main_hand"] == "hatchet"
    assert combat["loadout"]["layout"]["off_hand"] == "buckler"
    assert combat["loadout"]["layout"]["chest_armor"] == "jerkin"
    assert combat["math_model"]["modifiers"]["main_hand_damage_base"]["source"]
    assert combat["math_model"]["modifiers"]["armor"]["source"]
    assert combat["skills"]["skill_one_handed"] >= 20

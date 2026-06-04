import pytest

from src.backend.features.game_catalog.combat.resources.feints.availability import (
    ARCHERY_WEAPON_FEINTS,
    BASIC_ARCHERY_FEINTS,
    BASIC_FEINTS,
    FENCING_WEAPON_FEINTS,
    DUAL_WIELD_TACTICAL_FEINTS,
    MACING_WEAPON_FEINTS,
    RANGED_TACTICAL_FEINTS,
    SHIELD_TACTICAL_FEINTS,
    TWO_HANDED_TACTICAL_FEINTS,
)
from src.backend.features.items.dto.instance import RuntimeItemProjectionDTO
from src.backend.features.items.resources import get_base_by_id
from src.backend.features.monsters.dto.generation import GeneratedClan, MonsterGenerationContext
from src.backend.features.monsters.resources import get_family_config, get_starter_family_ids
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder
from src.backend.features.monsters.runtime.generation_builder import MonsterClanGenerationBuilder, _MemberPlan
from src.backend.features.monsters.runtime.generation_fields import build_member_tier
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags


class FakeRepository:
    async def get_clan_by_unique_hash(self, unique_hash: str):
        del unique_hash
        return None

    async def get_clans_by_context_hash(self, context_hash: str) -> list:
        del context_hash
        return []

    async def get_clan_members(self, clan_id) -> list:
        del clan_id
        return []

    async def create_clan_with_members(self, clan, members):
        clan.members.extend(members)
        for member in clan.members:
            member.clan = clan
        return clan

    async def update_clan_flavor(self, clan):
        return clan


class FakeItemGeneration:
    async def generate_runtime_projections(self, requests):
        projections = []
        for index, request in enumerate(requests):
            natural_key = request.runtime_metadata.get("natural_key")
            related_skill = {
                "rat_bite_claws": "skill_fencing",
                "rat_light_hide": "skill_light_armor",
                    "wolf_bite_claws": "skill_fencing",
                    "wolf_hide": "skill_light_armor",
                }.get(str(natural_key))
            if related_skill is None:
                related_skill = {
                    "knife": "skill_fencing",
                    "dagger": "skill_fencing",
                    "stiletto": "skill_fencing",
                    "rapier": "skill_fencing",
                    "main_gauche": "skill_fencing",
                    "katar": "skill_fencing",
                    "hatchet": "skill_macing",
                    "mace": "skill_macing",
                    "warhammer": "skill_macing",
                    "spear": "skill_polearms",
                    "quarterstaff": "skill_polearms",
                    "sling": "skill_archery",
                    "shortbow": "skill_archery",
                    "quiver_training": "skill_archery",
                    "quiver_fire": "skill_archery",
                    "buckler": "skill_shield_mastery",
                    "shield": "skill_shield_mastery",
                    "kite_shield": "skill_shield_mastery",
                    "jerkin": "skill_medium_armor",
                    "leather_armor": "skill_light_armor",
                    "plate_chest": "skill_heavy_armor",
                }.get(str(request.base_id), "skill_unarmed")
            if request.base_id == "amulet":
                related_skill = None
            projections.append(
                RuntimeItemProjectionDTO(
                    item_id=f"item-{index}",
                    owner_key=str(request.runtime_metadata["owner_key"]),
                    base_id=request.base_id,
                    item_type="ammo"
                    if request.target_slot == "quiver"
                    else (
                        "accessory"
                        if request.target_slot == "amulet"
                        else (
                        "shield"
                        if request.target_slot == "off_hand" and request.base_id in {"buckler", "shield", "kite_shield"}
                        else ("weapon" if request.target_slot in {"main_hand", "off_hand", "two_hand"} else "armor")
                        )
                    ),
                    slot=str(request.target_slot),
                    combat={
                        "power": 4,
                        "damage_spread": 0.0,
                        "implicit_bonuses": {},
                        "bonuses": {"main_hand_accuracy": "+0.01"},
                        "triggers": ["crit.weapon_flat_armor_gap_crit"],
                        "tags": ["shield"] if request.base_id in {"buckler", "shield", "kite_shield"} else [],
                        "related_skill": related_skill,
                    },
                    generation={"item_grade": request.item_grade, "rarity_tier": request.rarity_tier, "affixes": []},
                )
            )
        return projections


async def _build_member(family_id: str, variant_key: str | None = None):
    context = MonsterGenerationContext(
        zone_id="D4_0_1",
        biome_id="city_ruins",
        tier=1,
        tags=["mana_leak"],
        context_meta={
            "clan_flavor": {
                "name_ru": "Combat Test Clan",
                "description": "Authored combat fixture clan.",
                "encounter_texts": {
                    "patrol": "Patrol text.",
                    "ambush": "Ambush text.",
                    "lair": "Lair text.",
                    "random_meeting": "Random meeting text.",
                },
            }
        },
    )
    tags = normalize_tags(context.tags)
    context_hash = compute_context_hash(context.tier, context.biome_id, tags)
    unique_hash = compute_unique_clan_hash(family_id, context_hash)
    builder = MonsterClanGenerationBuilder(
        repository=FakeRepository(),
        item_generation=FakeItemGeneration(),
    )
    if variant_key is None:
        clan = await builder.generate_clan_template(
            family_id=family_id,
            context=context,
            context_hash=context_hash,
            unique_hash=unique_hash,
            normalized_tags=tags,
            reuse_existing=False,
        )
        member = clan.members[0]
        member.clan = clan
        return member

    family = get_family_config(family_id)
    assert family is not None
    variant = family.variants[variant_key]
    member_model = builder._member_model_for(family, variant)
    member_id = compute_unique_clan_hash(family_id, variant_key)
    import uuid

    plan = _MemberPlan(
        member_id=uuid.uuid5(uuid.NAMESPACE_DNS, member_id),
        owner_key=member_id,
        variant=variant,
        member_model=member_model,
        member_tier=build_member_tier(context.tier, variant, member_model),
    )
    item_requests = builder._build_item_requests(family, [plan], unique_hash)
    runtime_items = await builder._generate_runtime_items(item_requests)
    clan = GeneratedClan(
        id=uuid.uuid4(),
        family_id=family_id,
        identity_hash=unique_hash,
        context_identity={
            "tier": context.tier,
            "zone_id": context.zone_id,
            "biome_id": context.biome_id,
            "habitat": {"biome": context.habitat_biome, "keys": context.habitat_keys},
        },
        context_hash=context_hash,
        selected_traits=[],
        title=family_id,
        description=family_id,
        encounter_texts={
            "patrol": "Patrol text.",
            "ambush": "Ambush text.",
            "lair": "Lair text.",
            "random_meeting": "Random meeting text.",
        },
        generation_version=2,
        resource_version=str(family.resource_version),
    )
    member = builder._build_member_row(
        clan_id=clan.id,
        family=family,
        plan=plan,
        runtime_items=runtime_items,
        flavor={},
        context=context,
        identity_hash=unique_hash,
        selected_traits=[],
    )
    member.clan = clan
    return member


@pytest.mark.unit
def test_registry_loads_only_starter_families() -> None:
    assert get_starter_family_ids() == ("rat_swarm", "wolf_pack", "bandit_gang", "goblin_tribe")
    assert get_family_config("rat_swarm") is not None
    assert get_family_config("wolf_pack") is not None
    assert get_family_config("bandit_gang") is not None
    assert get_family_config("goblin_tribe") is not None
    assert get_family_config("anchor_sovereigns") is not None
    assert get_family_config("dragon_brood") is None


@pytest.mark.unit
@pytest.mark.parametrize("family_id", ["rat_swarm", "wolf_pack", "bandit_gang", "goblin_tribe"])
def test_starter_families_have_twelve_variants(family_id: str) -> None:
    family = get_family_config(family_id)

    assert family is not None
    assert len(family.variants) == 12


@pytest.mark.unit
@pytest.mark.parametrize(
    ("family_id", "expected_count"),
    [
        ("bandit_gang", 12),
        ("goblin_tribe", 12),
    ],
)
def test_humanoid_starter_families_have_full_variant_sets(family_id: str, expected_count: int) -> None:
    family = get_family_config(family_id)

    assert family is not None
    assert len(family.variants) == expected_count
    assert len(family.hierarchy.minions) >= 4
    assert len(family.hierarchy.veterans) >= 3
    assert len(family.hierarchy.elites) >= 3
    assert len(family.hierarchy.boss) >= 2


@pytest.mark.unit
@pytest.mark.parametrize("family_id", ["bandit_gang", "goblin_tribe"])
def test_humanoid_families_are_marked_for_equipment_loot(family_id: str) -> None:
    family = get_family_config(family_id)

    assert family is not None
    assert family.archetype == "humanoid"
    assert family.loot_profile is not None
    assert family.loot_profile.loot_mode == "equipment"
    assert family.loot_profile.allowed_loadout_slots == "full_humanoid"
    assert family.loot_profile.equipment_drop_policy == "fixed_loadout"
    assert family.loot_profile.drops_as_equipment is True
    assert family.loot_profile.equipment_quality is not None


@pytest.mark.unit
@pytest.mark.parametrize("family_id", ["bandit_gang", "goblin_tribe"])
def test_humanoid_family_fixed_loadout_slots_match_item_catalog(family_id: str) -> None:
    family = get_family_config(family_id)

    assert family is not None
    problems = []
    for variant in family.variants.values():
        for slot, base_id in variant.fixed_loadout.model_dump(exclude_none=True).items():
            base = get_base_by_id(base_id)
            if base is None:
                problems.append((variant.id, slot, base_id, "missing_base"))
                continue
            valid_slots = {str(base["slot"]), *(str(extra) for extra in base.get("extra_slots", []))}
            if slot not in valid_slots:
                problems.append((variant.id, slot, base_id, sorted(valid_slots)))

    assert problems == []


@pytest.mark.unit
@pytest.mark.parametrize("family_id", ["bandit_gang", "goblin_tribe"])
def test_humanoid_starter_variants_always_have_combat_weapon(family_id: str) -> None:
    family = get_family_config(family_id)

    assert family is not None
    missing_weapon = []
    invalid_weapon = []
    for variant in family.variants.values():
        loadout = variant.fixed_loadout.model_dump(exclude_none=True)
        weapon_id = loadout.get("main_hand") or loadout.get("two_hand")
        if not weapon_id:
            missing_weapon.append(variant.id)
            continue
        base = get_base_by_id(str(weapon_id))
        if base is None or base.get("type") != "weapon":
            invalid_weapon.append((variant.id, weapon_id, None if base is None else base.get("type")))

    assert missing_weapon == []
    assert invalid_weapon == []


@pytest.mark.unit
@pytest.mark.parametrize("family_id", ["rat_swarm", "wolf_pack"])
def test_beast_families_are_marked_for_salvage_loot(family_id: str) -> None:
    family = get_family_config(family_id)

    assert family is not None
    assert family.archetype == "beast"
    assert family.loot_profile is not None
    assert family.loot_profile.loot_mode == "salvage"
    assert family.loot_profile.allowed_loadout_slots == "natural_only"
    assert family.loot_profile.equipment_drop_policy == "none"
    assert family.loot_profile.drops_as_equipment is False
    assert family.loot_profile.materials


@pytest.mark.unit
@pytest.mark.parametrize("family_id", ["rat_swarm", "wolf_pack", "bandit_gang", "goblin_tribe"])
def test_starter_families_have_single_accessory_layer(family_id: str) -> None:
    from src.backend.features.monsters.resources.equipment_mapping import NATURAL_EQUIPMENT_MAPPINGS

    family = get_family_config(family_id)

    assert family is not None
    missing_accessory = []
    invalid_accessory = []
    for variant in family.variants.values():
        loadout = variant.fixed_loadout.model_dump(exclude_none=True)
        accessory_key = loadout.get("amulet")
        if not accessory_key:
            missing_accessory.append(variant.id)
            continue
        mapping = NATURAL_EQUIPMENT_MAPPINGS.get(str(accessory_key))
        base_id = mapping.base_id if mapping else str(accessory_key)
        base = get_base_by_id(base_id)
        if base is None or base.get("type") != "accessory" or base.get("slot") != "amulet":
            invalid_accessory.append((variant.id, accessory_key, base_id, None if base is None else base.get("slot")))

    assert missing_accessory == []
    assert invalid_accessory == []


@pytest.mark.unit
def test_bandit_gang_uses_authored_bow_and_armor_loadouts() -> None:
    family = get_family_config("bandit_gang")

    assert family is not None
    assert family.resource_version == 1.4
    expected = {
        "bandit_thug": (
            {"main_hand": "hatchet", "off_hand": "buckler", "chest_armor": "jerkin", "amulet": "amulet"},
            {"skill_macing", "skill_medium_armor"},
        ),
        "bandit_poacher": (
            {"two_hand": "shortbow", "quiver": "quiver_training", "chest_armor": "leather_armor", "amulet": "amulet"},
            {"skill_archery", "skill_ranged_combat", "skill_light_armor"},
        ),
        "bandit_lookout": (
            {"main_hand": "spear", "chest_armor": "leather_armor", "amulet": "amulet"},
            {"skill_polearms", "skill_light_armor"},
        ),
        "bandit_knife_rat": (
            {"main_hand": "dagger", "off_hand": "dagger", "chest_armor": "leather_armor", "amulet": "amulet"},
            {"skill_fencing", "skill_dual_wield", "skill_light_armor"},
        ),
        "bandit_raider": (
            {"main_hand": "mace", "off_hand": "shield", "chest_armor": "jerkin", "amulet": "amulet"},
            {"skill_macing", "skill_medium_armor", "skill_shield_mastery"},
        ),
        "bandit_billhook": (
            {"main_hand": "spear", "chest_armor": "jerkin", "amulet": "amulet"},
            {"skill_polearms", "skill_medium_armor"},
        ),
        "bandit_hedge_wizard": (
            {"two_hand": "quarterstaff", "chest_armor": "leather_armor", "amulet": "amulet"},
            {"skill_polearms", "skill_light_armor", "skill_two_handed"},
        ),
        "bandit_captain": (
            {"main_hand": "sword", "off_hand": "shield", "chest_armor": "jerkin", "amulet": "amulet"},
            {"skill_swords", "skill_medium_armor", "skill_shield_mastery", "skill_tactics", "skill_parrying"},
        ),
        "bandit_kingpin": (
            {"two_hand": "warhammer", "chest_armor": "plate_chest", "amulet": "amulet"},
            {"skill_macing", "skill_heavy_armor", "skill_two_handed", "skill_tactics", "skill_anatomy"},
        ),
        "bandit_warlord": (
            {"two_hand": "longbow", "quiver": "quiver_bodkin", "chest_armor": "leather_armor", "amulet": "amulet"},
            {"skill_archery", "skill_ranged_combat", "skill_light_armor", "skill_tactics", "skill_anatomy"},
        ),
        "bandit_cutthroat": (
            {"main_hand": "dagger", "off_hand": "dagger", "chest_armor": "leather_armor", "amulet": "amulet"},
            {
                "skill_fencing",
                "skill_light_armor",
                "skill_dual_wield",
                "skill_tactics",
                "skill_parrying",
                "skill_anatomy",
            },
        ),
        "bandit_blackguard": (
            {"main_hand": "mace", "off_hand": "shield", "chest_armor": "plate_chest", "amulet": "amulet"},
            {
                "skill_macing",
                "skill_heavy_armor",
                "skill_shield_mastery",
                "skill_tactics",
                "skill_parrying",
                "skill_anatomy",
            },
        ),
    }
    archer_variants = {"bandit_poacher", "bandit_warlord"}

    for variant_key, (loadout, skills) in expected.items():
        variant = family.variants[variant_key]
        actual_loadout = variant.fixed_loadout.model_dump(exclude_none=True)

        assert actual_loadout == loadout
        assert skills <= set(variant.skills)
        assert ("quiver" in actual_loadout) == (variant_key in archer_variants)
        if variant_key in archer_variants:
            assert actual_loadout["chest_armor"] == "leather_armor"
            assert "skill_light_armor" in variant.skills
            assert "skill_medium_armor" not in variant.skills
            assert "skill_heavy_armor" not in variant.skills


@pytest.mark.unit
def test_rat_swarm_uses_natural_loadouts_for_current_tactical_styles() -> None:
    family = get_family_config("rat_swarm")

    assert family is not None
    assert family.resource_version == 1.4
    expected = {
        "sewer_rat": ("dual", {"main_hand": "rat_bite_claws", "off_hand": "rat_offhand_bite"}),
        "scavenger_rat": ("dual", {"main_hand": "rat_bite_claws", "off_hand": "rat_offhand_bite"}),
        "swarm_rat": ("dual", {"main_hand": "rat_bite_claws", "off_hand": "rat_offhand_bite"}),
        "tunnel_rat": ("dual", {"main_hand": "rat_veteran_claws", "off_hand": "rat_offhand_bite"}),
        "pack_rat": ("shield", {"main_hand": "rat_veteran_claws", "off_hand": "rat_bone_growth"}),
        "screecher": ("ranged", {"two_hand": "rat_poison_spit", "quiver": "rat_poison_glands"}),
        "plague_rat": ("ranged", {"two_hand": "rat_poison_spit", "quiver": "rat_poison_glands"}),
        "rotfang": ("two_handed", {"two_hand": "rat_crushing_bite"}),
        "blight_carrier": ("shield", {"main_hand": "rat_elite_claws", "off_hand": "rat_spiked_growth"}),
        "rat_brute": ("two_handed", {"two_hand": "rat_crushing_bite"}),
        "brood_alpha": ("shield", {"main_hand": "rat_boss_claws", "off_hand": "rat_spiked_growth"}),
        "rat_king": ("ranged", {"two_hand": "rat_poison_spit", "quiver": "rat_poison_glands"}),
    }
    required_skills = {
        "dual": {"skill_fencing", "skill_dual_wield"},
        "shield": {"skill_fencing", "skill_shield_mastery"},
        "ranged": {"skill_archery", "skill_ranged_combat"},
        "two_handed": {"skill_macing", "skill_two_handed"},
    }

    for variant_key, (style, loadout_subset) in expected.items():
        variant = family.variants[variant_key]
        loadout = variant.fixed_loadout.model_dump(exclude_none=True)

        assert loadout_subset.items() <= loadout.items()
        assert loadout["amulet"] == "rat_plague_gland"
        assert required_skills[style] <= set(variant.skills)


@pytest.mark.unit
def test_goblin_tribe_uses_balanced_progression_loadouts_and_tags() -> None:
    family = get_family_config("goblin_tribe")

    assert family is not None
    assert family.resource_version == 1.4
    expected = {
        "goblin_sneak": (
            {"main_hand": "knife", "off_hand": "knife", "chest_armor": "leather_armor", "amulet": "amulet"},
            {"skill_fencing", "skill_dual_wield", "skill_light_armor"},
            {"stealth", "dual_wield", "knife"},
        ),
        "goblin_scavenger": (
            {"main_hand": "mace", "off_hand": "buckler", "chest_armor": "leather_armor", "amulet": "amulet"},
            {"skill_macing", "skill_shield_mastery", "skill_light_armor"},
            {"scavenger", "scrap", "buckler"},
        ),
        "goblin_cutter": (
            {"main_hand": "dagger", "off_hand": "knife", "chest_armor": "leather_armor", "amulet": "amulet"},
            {"skill_fencing", "skill_dual_wield", "skill_light_armor"},
            {"knife", "bleeder", "dual_wield"},
        ),
        "goblin_sparkpick": (
            {"main_hand": "hatchet", "off_hand": "buckler", "chest_armor": "leather_armor", "amulet": "amulet"},
            {"skill_macing", "skill_shield_mastery", "skill_light_armor"},
            {"scrap", "ether", "buckler"},
        ),
        "goblin_spearman": (
            {"main_hand": "spear", "off_hand": "shield", "chest_armor": "jerkin", "amulet": "amulet"},
            {"skill_polearms", "skill_medium_armor", "skill_shield_mastery"},
            {"infantry", "shield"},
        ),
        "goblin_slinger": (
            {"two_hand": "shortbow", "quiver": "quiver_training", "chest_armor": "leather_armor", "amulet": "amulet"},
            {"skill_archery", "skill_ranged_combat", "skill_light_armor"},
            {"ranged", "archer", "quiver"},
        ),
        "goblin_scrapguard": (
            {"main_hand": "mace", "off_hand": "shield", "chest_armor": "jerkin", "amulet": "amulet"},
            {"skill_macing", "skill_medium_armor", "skill_shield_mastery"},
            {"shield", "defender", "scrap"},
        ),
        "goblin_tinkerer": (
            {"main_hand": "rapier", "off_hand": "buckler", "chest_armor": "jerkin", "amulet": "amulet"},
            {"skill_fencing", "skill_shield_mastery", "skill_medium_armor", "skill_tactics"},
            {"engineer", "duelist", "scrap", "buckler"},
        ),
        "goblin_bomber": (
            {"two_hand": "shortbow", "quiver": "quiver_fire", "chest_armor": "jerkin", "amulet": "amulet"},
            {"skill_archery", "skill_medium_armor", "skill_ranged_combat", "skill_tactics"},
            {"bomber", "explosives", "archer", "fire_arrows"},
        ),
        "goblin_trapmaster": (
            {"main_hand": "stiletto", "off_hand": "main_gauche", "chest_armor": "jerkin", "amulet": "amulet"},
            {"skill_fencing", "skill_dual_wield", "skill_medium_armor", "skill_tactics", "skill_anatomy"},
            {"trapper", "controller", "dual_wield", "precision"},
        ),
        "goblin_chief": (
            {"main_hand": "battle_axe", "off_hand": "kite_shield", "chest_armor": "plate_chest", "amulet": "amulet"},
            {"skill_macing", "skill_shield_mastery", "skill_heavy_armor", "skill_tactics", "skill_anatomy"},
            {"leader", "commander", "heavy_armor", "shield"},
        ),
        "scrap_king": (
            {"two_hand": "warhammer", "chest_armor": "plate_chest", "amulet": "amulet"},
            {"skill_macing", "skill_heavy_armor", "skill_two_handed", "skill_tactics", "skill_anatomy"},
            {"king", "heavy_armor", "two_handed", "scrap"},
        ),
    }

    for variant_key, (loadout, skills, tags) in expected.items():
        variant = family.variants[variant_key]

        assert variant.fixed_loadout.model_dump(exclude_none=True) == loadout
        assert skills <= set(variant.skills)
        assert tags <= set(variant.extra_tags)


@pytest.mark.unit
def test_wolf_pack_uses_natural_loadouts_for_current_pack_styles() -> None:
    family = get_family_config("wolf_pack")

    assert family is not None
    assert family.resource_version == 1.4
    expected = {
        "cub": (
            "dual",
            {
                "main_hand": "wolf_young_fangs",
                "off_hand": "wolf_young_claws",
                "chest_armor": "wolf_hide",
            },
        ),
        "runner": (
            "dual",
            {
                "main_hand": "wolf_young_fangs",
                "off_hand": "wolf_young_claws",
                "chest_armor": "wolf_hide",
            },
        ),
        "mangy_biter": (
            "dual",
            {
                "main_hand": "wolf_young_fangs",
                "off_hand": "wolf_locking_fangs",
                "chest_armor": "wolf_hide",
            },
        ),
        "stalker": (
            "dual",
            {
                "main_hand": "wolf_bite_claws",
                "off_hand": "wolf_raking_claws",
                "chest_armor": "wolf_hide",
            },
        ),
        "flanker": (
            "dual",
            {
                "main_hand": "wolf_bite_claws",
                "off_hand": "wolf_raking_claws",
                "chest_armor": "wolf_medium_hide",
            },
        ),
        "snapper": (
            "dual",
            {
                "main_hand": "wolf_bite_claws",
                "off_hand": "wolf_locking_fangs",
                "chest_armor": "wolf_hide",
            },
        ),
        "pack_leader": (
            "shield",
            {
                "main_hand": "wolf_elite_fangs",
                "off_hand": "wolf_braced_mane",
                "chest_armor": "wolf_medium_hide",
            },
        ),
        "dire_wolf": (
            "shield",
            {
                "main_hand": "wolf_elite_fangs",
                "off_hand": "wolf_bone_shoulders",
                "chest_armor": "wolf_heavy_hide",
            },
        ),
        "old_fang": (
            "dual",
            {
                "main_hand": "wolf_elite_fangs",
                "off_hand": "wolf_locking_fangs",
                "chest_armor": "wolf_medium_hide",
            },
        ),
        "alpha_prime": (
            "shield",
            {
                "main_hand": "wolf_alpha_fangs",
                "off_hand": "wolf_bone_shoulders",
                "chest_armor": "wolf_heavy_hide",
            },
        ),
        "winter_maw": (
            "shield",
            {
                "main_hand": "wolf_alpha_fangs",
                "off_hand": "wolf_braced_mane",
                "chest_armor": "wolf_heavy_hide",
            },
        ),
        "blood_howl": (
            "dual",
            {
                "main_hand": "wolf_alpha_fangs",
                "off_hand": "wolf_raking_claws",
                "chest_armor": "wolf_heavy_hide",
            },
        ),
    }
    required_skills = {
        "dual": {"skill_fencing", "skill_dual_wield"},
        "shield": {"skill_fencing", "skill_shield_mastery"},
    }

    for variant_key, (style, loadout_subset) in expected.items():
        variant = family.variants[variant_key]
        loadout = variant.fixed_loadout.model_dump(exclude_none=True)

        assert set(loadout) == {"main_hand", "off_hand", "chest_armor", "amulet"}
        assert loadout_subset.items() <= loadout.items()
        assert loadout["amulet"] == "wolf_pack_mark"
        assert required_skills[style] <= set(variant.skills)


@pytest.mark.unit
def test_monster_natural_equipment_is_registered_as_item_base() -> None:
    from src.backend.features.monsters.resources.equipment_mapping import NATURAL_EQUIPMENT_MAPPINGS

    # Natural equipment uses transmog: each natural key maps to a player item base_id
    rat_weapon_mapping = NATURAL_EQUIPMENT_MAPPINGS["rat_bite_claws"]
    rat_armor_mapping = NATURAL_EQUIPMENT_MAPPINGS["rat_light_hide"]
    anchor_weapon_mapping = NATURAL_EQUIPMENT_MAPPINGS["anchor_gravity_storm_lance"]
    anchor_armor_mapping = NATURAL_EQUIPMENT_MAPPINGS["anchor_projection_aegis"]

    assert rat_weapon_mapping.item_kind == "weapon"
    assert rat_weapon_mapping.default_slot == "main_hand"
    assert rat_weapon_mapping.name_ru is not None

    assert rat_armor_mapping.item_kind == "armor"
    assert rat_armor_mapping.default_slot == "chest_armor"

    # The base_ids must resolve to real player item entries
    rat_weapon_base = get_base_by_id(rat_weapon_mapping.base_id)
    rat_armor_base = get_base_by_id(rat_armor_mapping.base_id)
    anchor_weapon_base = get_base_by_id(anchor_weapon_mapping.base_id)
    anchor_armor_base = get_base_by_id(anchor_armor_mapping.base_id)

    assert rat_weapon_base is not None, f"{rat_weapon_mapping.base_id!r} not in item catalog"
    assert rat_weapon_base["type"] == "weapon"
    assert rat_armor_base is not None, f"{rat_armor_mapping.base_id!r} not in item catalog"
    assert rat_armor_base["type"] == "armor"
    assert anchor_weapon_base is not None, f"{anchor_weapon_mapping.base_id!r} not in item catalog"
    assert anchor_weapon_base["type"] == "weapon"
    assert anchor_armor_base is not None, f"{anchor_armor_mapping.base_id!r} not in item catalog"
    assert anchor_armor_base["type"] == "armor"


@pytest.mark.unit
def test_anchor_sovereigns_family_defines_four_tier_seven_bosses() -> None:
    family = get_family_config("anchor_sovereigns")

    assert family is not None
    assert family.archetype == "unknown"
    assert family.hierarchy.boss == [
        "north_stasis_sovereign",
        "south_entropy_sovereign",
        "west_gravity_sovereign",
        "east_evolution_sovereign",
    ]
    assert all(variant.role == "boss" for variant in family.variants.values())
    assert all(variant.min_tier == 7 and variant.max_tier == 7 for variant in family.variants.values())
    assert family.variants["north_stasis_sovereign"].base_stats.memory > 200
    assert family.variants["south_entropy_sovereign"].base_stats.strength > 200
    assert family.variants["west_gravity_sovereign"].base_stats.perception > 200
    assert family.variants["east_evolution_sovereign"].base_stats.agility > 200
    assert family.variants["north_stasis_sovereign"].fixed_loadout.model_dump(exclude_none=True) == {
        "main_hand": "anchor_stasis_crown_blade",
        "off_hand": "shield",
        "chest_armor": "anchor_projection_aegis",
    }
    assert family.variants["south_entropy_sovereign"].fixed_loadout.model_dump(exclude_none=True) == {
        "two_hand": "anchor_entropy_cinder_maul",
        "chest_armor": "anchor_projection_aegis",
    }
    assert family.variants["west_gravity_sovereign"].fixed_loadout.model_dump(exclude_none=True) == {
        "main_hand": "anchor_gravity_storm_lance",
        "chest_armor": "anchor_projection_aegis",
    }
    assert family.variants["east_evolution_sovereign"].fixed_loadout.model_dump(exclude_none=True) == {
        "main_hand": "anchor_evolution_bloom_talons",
        "off_hand": "anchor_evolution_bloom_talons",
        "chest_armor": "anchor_projection_aegis",
    }
    assert "skill_shield_mastery" in family.variants["north_stasis_sovereign"].skills
    assert "skill_two_handed" in family.variants["south_entropy_sovereign"].skills
    assert "skill_one_handed" not in family.variants["west_gravity_sovereign"].skills
    assert "skill_dual_wield" in family.variants["east_evolution_sovereign"].skills
    for variant in family.variants.values():
        assert "skill_tactics" in variant.skills
        assert "skill_anatomy" in variant.skills
    from src.backend.features.monsters.resources.equipment_mapping import NATURAL_EQUIPMENT_MAPPINGS

    for variant in family.variants.values():
        for _slot, natural_key in variant.fixed_loadout.model_dump(exclude_none=True).items():
            if natural_key == "shield":
                continue  # abstract shield slot — no direct base item
            # Fixed loadout values are natural keys resolved through NATURAL_EQUIPMENT_MAPPINGS
            mapping = NATURAL_EQUIPMENT_MAPPINGS.get(natural_key)
            assert mapping is not None, f"{natural_key!r} not in NATURAL_EQUIPMENT_MAPPINGS"
            base = get_base_by_id(mapping.base_id)
            assert base is not None, f"transmog base_id {mapping.base_id!r} not in item catalog"


@pytest.mark.unit
async def test_rat_beast_profile_builds_combat_ready_context() -> None:
    monster = await _build_member("rat_swarm")
    snapshot = MonsterCombatActorInputBuilder().build_snapshot(monster)
    combat = snapshot["combat"]

    assert combat["math_model"]["attributes"]["strength"]["base"] > 0
    assert combat["math_model"]["attributes"]["intellect"]["base"] >= 0
    assert combat["math_model"]["modifiers"]["main_hand_damage_base"]["base"] > 0
    assert combat["loadout"]["layout"]["main_hand"] == "skill_fencing"
    assert combat["loadout"]["layout"]["off_hand"] == "skill_fencing"
    assert combat["loadout"]["layout"]["main_hand_trigger"] == "crit.weapon_flat_armor_gap_crit"
    assert combat["loadout"]["layout"]["body"] == "skill_light_armor"
    assert combat["loadout"]["equipment_layout"]["main_hand"]
    assert combat["loadout"]["equipment_layout"]["off_hand"]
    assert combat["loadout"]["equipment_layout"]["chest_armor"]
    assert combat["loadout"]["equipment_layout"]["amulet"]
    assert combat["math_model"]["modifiers"]["magic_armor"]["base"] > 0
    assert combat["loadout"]["known_feints"] == [*BASIC_FEINTS, *FENCING_WEAPON_FEINTS, *DUAL_WIELD_TACTICAL_FEINTS]
    assert combat["loadout"]["known_abilities"] == []
    assert combat["skills"]["skill_fencing"] == pytest.approx(0.1429)
    assert snapshot["status"]["hp"]["max"] > 0


@pytest.mark.unit
@pytest.mark.parametrize(
    ("variant_key", "expected_layout", "expected_feints"),
    [
        (
            "pack_rat",
            {"main_hand": "skill_fencing", "off_hand": "skill_shield_mastery"},
            [*BASIC_FEINTS, *FENCING_WEAPON_FEINTS, *SHIELD_TACTICAL_FEINTS],
        ),
        (
            "screecher",
            {"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"},
            [*BASIC_ARCHERY_FEINTS, *ARCHERY_WEAPON_FEINTS, *RANGED_TACTICAL_FEINTS],
        ),
        (
            "rotfang",
            {"main_hand": "skill_macing", "tactical_style": "skill_two_handed"},
            [*BASIC_FEINTS, *MACING_WEAPON_FEINTS, *TWO_HANDED_TACTICAL_FEINTS],
        ),
    ],
)
async def test_rat_tactical_variants_build_expected_combat_layouts(
    variant_key: str,
    expected_layout: dict[str, str],
    expected_feints: list[str],
) -> None:
    monster = await _build_member("rat_swarm", variant_key)
    combat = MonsterCombatActorInputBuilder().build_snapshot(monster)["combat"]

    for slot, skill_key in expected_layout.items():
        assert combat["loadout"]["layout"][slot] == skill_key
    assert combat["loadout"]["known_feints"] == expected_feints


@pytest.mark.unit
@pytest.mark.parametrize(
    ("variant_key", "expected_layout", "expected_feints"),
    [
        (
            "flanker",
            {
                "main_hand": "skill_fencing",
                "off_hand": "skill_fencing",
                "tactical_style": "skill_dual_wield",
            },
            [*BASIC_FEINTS, *FENCING_WEAPON_FEINTS, *DUAL_WIELD_TACTICAL_FEINTS],
        ),
        (
            "pack_leader",
            {
                "main_hand": "skill_fencing",
                "off_hand": "skill_shield_mastery",
                "tactical_style": "skill_shield_mastery",
            },
            [*BASIC_FEINTS, *FENCING_WEAPON_FEINTS, *SHIELD_TACTICAL_FEINTS],
        ),
    ],
)
async def test_wolf_tactical_variants_build_expected_combat_layouts(
    variant_key: str,
    expected_layout: dict[str, str],
    expected_feints: list[str],
) -> None:
    monster = await _build_member("wolf_pack", variant_key)
    combat = MonsterCombatActorInputBuilder().build_snapshot(monster)["combat"]

    for slot, skill_key in expected_layout.items():
        assert combat["loadout"]["layout"][slot] == skill_key
    assert combat["loadout"]["equipment_layout"]["amulet"]
    assert combat["math_model"]["modifiers"]["magic_armor"]["base"] > 0
    assert combat["loadout"]["known_feints"] == expected_feints


@pytest.mark.unit
async def test_bandit_humanoid_loadout_resolves_into_modifiers_and_layout() -> None:
    monster = await _build_member("bandit_gang", "bandit_thug")
    combat = MonsterCombatActorInputBuilder().build_snapshot(monster)["combat"]

    assert combat["loadout"]["layout"]["main_hand"] == "skill_macing"
    assert combat["loadout"]["layout"]["off_hand"] == "skill_shield_mastery"
    assert combat["loadout"]["layout"]["body"] == "skill_medium_armor"
    assert combat["loadout"]["equipment_layout"]["main_hand"]
    assert combat["loadout"]["equipment_layout"]["off_hand"]
    assert combat["loadout"]["equipment_layout"]["chest_armor"]
    assert combat["math_model"]["modifiers"]["main_hand_damage_base"]["base"] > 0
    assert combat["math_model"]["modifiers"]["main_hand_accuracy"]["base"] == 0.0
    assert "family:bandit_gang" not in combat["math_model"]["modifiers"]["accuracy"]["source"]
    assert combat["math_model"]["modifiers"]["armor"]["base"] > 0
    assert combat["skills"]["skill_macing"] == pytest.approx(0.1429)
    assert combat["loadout"]["known_feints"] == [*BASIC_FEINTS, *MACING_WEAPON_FEINTS, *SHIELD_TACTICAL_FEINTS]


@pytest.mark.unit
async def test_goblin_humanoid_loadout_resolves_into_damage_and_accuracy() -> None:
    monster = await _build_member("goblin_tribe", "goblin_scrapguard")
    combat = MonsterCombatActorInputBuilder().build_snapshot(monster)["combat"]

    assert combat["loadout"]["layout"]["main_hand"] == "skill_macing"
    assert combat["loadout"]["layout"]["off_hand"] == "skill_shield_mastery"
    assert combat["math_model"]["modifiers"]["main_hand_damage_base"]["base"] > 0
    assert combat["math_model"]["modifiers"]["main_hand_accuracy"]["base"] == 0.0
    assert "family:goblin_tribe" not in combat["math_model"]["modifiers"]["accuracy"]["source"]
    assert combat["math_model"]["modifiers"]["shield_guard_power"]["base"] > 0
    assert combat["skills"]["skill_macing"] == pytest.approx(0.1429)

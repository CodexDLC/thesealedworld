import pytest

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
                    "dagger": "skill_fencing",
                    "hatchet": "skill_macing",
                    "mace": "skill_macing",
                    "warhammer": "skill_macing",
                    "spear": "skill_polearms",
                    "quarterstaff": "skill_polearms",
                    "sling": "skill_archery",
                    "shortbow": "skill_archery",
                    "buckler": "skill_shield_mastery",
                    "shield": "skill_shield_mastery",
                    "jerkin": "skill_medium_armor",
                    "leather_armor": "skill_light_armor",
                }.get(str(request.base_id), "skill_unarmed")
            projections.append(
                RuntimeItemProjectionDTO(
                    item_id=f"item-{index}",
                    owner_key=str(request.runtime_metadata["owner_key"]),
                    base_id=request.base_id,
                    item_type="shield"
                    if request.target_slot == "off_hand" and request.base_id in {"buckler", "shield"}
                    else ("weapon" if request.target_slot in {"main_hand", "two_hand"} else "armor"),
                    slot=str(request.target_slot),
                    combat={
                        "power": 4,
                        "damage_spread": 0.0,
                        "implicit_bonuses": {},
                        "bonuses": {"main_hand_accuracy": "+0.01"},
                        "triggers": ["crit.weapon_flat_armor_gap_crit"],
                        "tags": ["shield"] if request.base_id == "buckler" else [],
                        "related_skill": related_skill,
                    },
                    generation={"item_grade": request.item_grade, "rarity_tier": request.rarity_tier, "affixes": []},
                )
            )
        return projections


async def _build_member(family_id: str, variant_key: str | None = None):
    context = MonsterGenerationContext(zone_id="D4_0_1", biome_id="city_ruins", tier=1, tags=["mana_leak"])
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
        tier=context.tier,
        zone_id=context.zone_id,
        context_hash=context_hash,
        unique_hash=unique_hash,
        raw_tags={},
        flavor_content={},
        name_ru=family_id,
        description=family_id,
    )
    member = builder._build_member_row(
        clan_id=clan.id,
        family=family,
        plan=plan,
        runtime_items=runtime_items,
        flavor={},
        context=context,
        unique_hash=unique_hash,
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
    assert family.variants["north_stasis_sovereign"].skill_overrides["skill_shield_mastery"] == 1.0
    assert family.variants["south_entropy_sovereign"].skill_overrides["skill_two_handed"] == 1.0
    assert family.variants["west_gravity_sovereign"].skill_overrides["skill_one_handed"] == 1.0
    assert family.variants["east_evolution_sovereign"].skill_overrides["skill_dual_wield"] == 1.0
    for variant in family.variants.values():
        assert all(value == 1.0 for value in variant.skill_overrides.values())
    from src.backend.features.monsters.resources.equipment_mapping import NATURAL_EQUIPMENT_MAPPINGS

    for variant in family.variants.values():
        for slot, natural_key in variant.fixed_loadout.model_dump(exclude_none=True).items():
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
    assert combat["loadout"]["layout"]["main_hand_trigger"] == "crit.weapon_flat_armor_gap_crit"
    assert combat["loadout"]["layout"]["body"] == "skill_light_armor"
    assert combat["loadout"]["equipment_layout"]["main_hand"]
    assert combat["loadout"]["equipment_layout"]["chest_armor"]
    assert "measured_strike" in combat["loadout"]["known_feints"]
    assert "close_grapple" not in combat["loadout"]["known_feints"]
    assert combat["skills"]["skill_fencing"] >= 0.2
    assert snapshot["status"]["hp"]["max"] > 0


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
    assert combat["math_model"]["modifiers"]["accuracy"]["source"]["family:bandit_gang"] == pytest.approx(-0.10)
    assert combat["math_model"]["modifiers"]["armor"]["base"] > 0
    assert combat["skills"]["skill_macing"] >= 0.2
    assert "measured_strike" in combat["loadout"]["known_feints"]
    assert "guard_breaker" not in combat["loadout"]["known_feints"]


@pytest.mark.unit
async def test_goblin_humanoid_loadout_resolves_into_damage_and_accuracy() -> None:
    monster = await _build_member("goblin_tribe", "goblin_scrapguard")
    combat = MonsterCombatActorInputBuilder().build_snapshot(monster)["combat"]

    assert combat["loadout"]["layout"]["main_hand"] == "skill_macing"
    assert combat["loadout"]["layout"]["off_hand"] == "skill_shield_mastery"
    assert combat["math_model"]["modifiers"]["main_hand_damage_base"]["base"] > 0
    assert combat["math_model"]["modifiers"]["main_hand_accuracy"]["base"] == 0.0
    assert combat["math_model"]["modifiers"]["accuracy"]["source"]["family:goblin_tribe"] == pytest.approx(-0.10)
    assert combat["math_model"]["modifiers"]["shield_guard_power"]["base"] > 0
    assert combat["skills"]["skill_macing"] >= 0.2

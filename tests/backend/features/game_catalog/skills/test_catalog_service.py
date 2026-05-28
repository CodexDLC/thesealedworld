from src.backend.features.game_catalog.skills.dto import SkillGroup, SkillUiGroup
from src.backend.features.game_catalog.skills.resources.contracts import SKILL_SURFACE_CONTRACTS
from src.backend.features.game_catalog.skills.services import SkillCatalogService

DOC_SKILL_KEYS = {
    "skill_swords",
    "skill_fencing",
    "skill_polearms",
    "skill_macing",
    "skill_archery",
    "skill_unarmed",
    "skill_ranged_combat",
    "skill_two_handed",
    "skill_shield_mastery",
    "skill_dual_wield",
    "skill_light_armor",
    "skill_medium_armor",
    "skill_heavy_armor",
    "skill_parrying",
    "skill_anatomy",
    "skill_tactics",
    "skill_first_aid",
    "skill_weapon_craft",
    "skill_armor_craft",
    "skill_jewelry_craft",
    "skill_alchemy",
    "skill_engineering",
    "skill_artifact_craft",
    "skill_mining",
    "skill_woodcutting",
    "skill_skinning",
    "skill_herbalism",
    "skill_hunting",
    "skill_archaeology",
    "skill_taming",
    "skill_adaptation",
    "skill_scouting",
    "skill_pathfinder",
    "skill_accounting",
    "skill_brokerage",
    "skill_contracts",
    "skill_trade_relations",
    "skill_organization",
    "skill_leadership",
    "skill_team_spirit",
    "skill_egoism",
}


def test_skill_catalog_loads_public_text_projection():
    catalog = SkillCatalogService()

    public_text = catalog.all_public_text()

    assert "skill_swords" in public_text
    assert public_text["skill_swords"]["title"] == "Владение мечами"
    assert public_text["skill_swords"]["description"]
    assert public_text["skill_swords"]["group"] == "combat"
    assert public_text["skill_swords"]["ui_group"] == "weapon_mastery"
    assert "stat_weights" not in public_text["skill_swords"]


def test_skill_catalog_public_descriptions_explain_effects():
    catalog = SkillCatalogService()

    public_text = catalog.all_public_text()

    for skill_key, item in public_text.items():
        description = str(item["description"])
        assert "\n\nДаёт:" in description, skill_key
        assert "DATA_MISSING" not in description, skill_key

    assert "штрафов оружия к точности" in str(public_text["skill_swords"]["description"])
    assert "шанс парирования" in str(public_text["skill_parrying"]["description"])
    assert "блоком щитом" in str(public_text["skill_parrying"]["description"])
    assert "Shield Mastery" not in str(public_text["skill_parrying"]["description"])
    assert "до 50% входящего урона" in str(public_text["skill_shield_mastery"]["description"])
    assert "не парирование в 0 урона" in str(public_text["skill_shield_mastery"]["description"])
    assert "до 50% на 100 мастерства" in str(public_text["skill_dual_wield"]["description"])
    assert "сама не может запускать еще одну" in str(public_text["skill_dual_wield"]["description"])
    assert "жестко режет кап уклонения" in str(public_text["skill_heavy_armor"]["description"])
    assert "предпросмотр ценного лута" in str(public_text["skill_scouting"]["description"])


def test_skill_catalog_uses_prefixed_skill_keys():
    catalog = SkillCatalogService()

    skills = catalog.skills
    unprefixed = sorted(skill.skill_key for skill in skills if not skill.skill_key.startswith("skill_"))

    assert unprefixed == []
    assert catalog.get("skill_scouting") is not None
    assert catalog.get("skill_pathfinder") is not None
    assert catalog.get("skill_engineering") is not None


def test_skill_catalog_matches_documented_contract():
    catalog = SkillCatalogService()
    keys = {skill.skill_key for skill in catalog.skills}

    assert keys == DOC_SKILL_KEYS
    assert all(key.startswith("skill_") for key in keys)
    assert {skill.group for skill in catalog.skills} == {
        SkillGroup.COMBAT,
        SkillGroup.WORLD,
        SkillGroup.CRAFTING,
        SkillGroup.SOCIAL,
    }
    assert {skill.ui_group for skill in catalog.skills} == {
        SkillUiGroup.WEAPON_MASTERY,
        SkillUiGroup.TACTICAL,
        SkillUiGroup.ARMOR,
        SkillUiGroup.COMBAT_SUPPORT,
        SkillUiGroup.GATHERING,
        SkillUiGroup.SURVIVAL,
        SkillUiGroup.CRAFTING,
        SkillUiGroup.TRADE,
        SkillUiGroup.LEADERSHIP,
    }


def test_armor_skill_stat_weights_match_current_design():
    catalog = SkillCatalogService()
    light_armor = catalog.get("skill_light_armor")
    medium_armor = catalog.get("skill_medium_armor")
    heavy_armor = catalog.get("skill_heavy_armor")

    assert light_armor is not None
    assert medium_armor is not None
    assert heavy_armor is not None
    assert light_armor.stat_weights == {"agility": 2, "endurance": 1, "perception": 1}
    assert medium_armor.stat_weights == {
        "agility": 1,
        "endurance": 1,
        "perception": 1,
        "strength": 1,
    }
    assert heavy_armor.stat_weights == {"endurance": 2, "mental": 1, "strength": 1}


def test_tactical_skill_stat_weights_match_current_design():
    catalog = SkillCatalogService()
    ranged_combat = catalog.get("skill_ranged_combat")
    two_handed = catalog.get("skill_two_handed")
    shield_mastery = catalog.get("skill_shield_mastery")
    dual_wield = catalog.get("skill_dual_wield")

    assert ranged_combat is not None
    assert catalog.get("skill_one_handed") is None
    assert two_handed is not None
    assert shield_mastery is not None
    assert dual_wield is not None
    assert ranged_combat.stat_weights == {"agility": 1, "memory": 1, "perception": 1, "prediction": 1}
    assert two_handed.stat_weights == {"endurance": 1, "perception": 1, "strength": 2}
    assert shield_mastery.stat_weights == {"endurance": 1, "memory": 1, "mental": 1, "strength": 1}
    assert dual_wield.stat_weights == {"agility": 1, "memory": 1, "perception": 1, "prediction": 1}


def test_weapon_mastery_skill_stat_weights_match_current_design():
    catalog = SkillCatalogService()
    swords = catalog.get("skill_swords")
    fencing = catalog.get("skill_fencing")
    polearms = catalog.get("skill_polearms")
    macing = catalog.get("skill_macing")
    archery = catalog.get("skill_archery")
    unarmed = catalog.get("skill_unarmed")

    assert swords is not None
    assert fencing is not None
    assert polearms is not None
    assert macing is not None
    assert archery is not None
    assert unarmed is not None
    assert swords.stat_weights == {"agility": 1, "perception": 1, "prediction": 1, "strength": 1}
    assert fencing.stat_weights == {"agility": 2, "perception": 1, "prediction": 1}
    assert polearms.stat_weights == {"agility": 1, "perception": 2, "strength": 1}
    assert macing.stat_weights == {"endurance": 1, "mental": 1, "strength": 2}
    assert archery.stat_weights == {"agility": 1, "perception": 2, "prediction": 1}
    assert unarmed.stat_weights == {"agility": 1, "endurance": 1, "mental": 1, "strength": 1}


def test_combat_support_skill_stat_weights_match_current_design():
    catalog = SkillCatalogService()
    parrying = catalog.get("skill_parrying")
    anatomy = catalog.get("skill_anatomy")
    tactics = catalog.get("skill_tactics")

    assert parrying is not None
    assert anatomy is not None
    assert tactics is not None
    assert parrying.stat_weights == {"agility": 1, "perception": 2, "prediction": 1}
    assert anatomy.stat_weights == {"intellect": 2, "memory": 1, "perception": 1}
    assert tactics.stat_weights == {"intellect": 2, "memory": 1, "prediction": 1}


def test_runtime_world_skill_stat_weights_match_current_design():
    catalog = SkillCatalogService()
    adaptation = catalog.get("skill_adaptation")
    scouting = catalog.get("skill_scouting")
    pathfinder = catalog.get("skill_pathfinder")
    hunting = catalog.get("skill_hunting")
    taming = catalog.get("skill_taming")

    assert adaptation is not None
    assert scouting is not None
    assert pathfinder is not None
    assert hunting is not None
    assert taming is not None
    assert adaptation.stat_weights == {"endurance": 2, "memory": 1, "mental": 1}
    assert scouting.stat_weights == {"memory": 1, "perception": 2, "prediction": 1}
    assert pathfinder.stat_weights == {"endurance": 1, "memory": 1, "perception": 2}
    assert hunting.stat_weights == {"agility": 1, "perception": 2, "prediction": 1}
    assert taming.stat_weights == {"memory": 1, "mental": 1, "projection": 2}


def test_skill_surface_contracts_reference_catalog_keys():
    catalog = SkillCatalogService()
    keys = set(catalog.by_key)

    assert set(SKILL_SURFACE_CONTRACTS) == {"actor_snapshot", "encounter", "crafting", "inventory"}
    for surface_keys in SKILL_SURFACE_CONTRACTS.values():
        assert set(surface_keys) <= keys
        assert all(key.startswith("skill_") for key in surface_keys)

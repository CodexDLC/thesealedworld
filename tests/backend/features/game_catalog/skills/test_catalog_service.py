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
    "skill_one_handed",
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


def test_skill_surface_contracts_reference_catalog_keys():
    catalog = SkillCatalogService()
    keys = set(catalog.by_key)

    assert set(SKILL_SURFACE_CONTRACTS) == {"actor_snapshot", "encounter", "crafting", "inventory"}
    for surface_keys in SKILL_SURFACE_CONTRACTS.values():
        assert set(surface_keys) <= keys
        assert all(key.startswith("skill_") for key in surface_keys)

import json
from pathlib import Path
from typing import Any

from src.backend.features.game_catalog.skills.services import SkillCatalogService
from src.backend.features.items.dto.instance import ItemGenerationRequestDTO
from src.backend.features.items.runtime.item_factory import ItemFactory
from src.backend.features.items.services.catalog_service import ItemCatalogService

QUEST_DIR = (
    Path(__file__).resolve().parents[4]
    / "src"
    / "backend"
    / "features"
    / "scenario"
    / "resources"
    / "json"
    / "awakening_rift"
)


def test_awakening_rift_reward_items_exist_in_item_catalog() -> None:
    item_catalog = ItemCatalogService.load_default()
    item_factory = ItemFactory(item_catalog)

    missing = sorted(
        item_id for item_id in _collect_reward_values("loot_queue") if item_id not in item_catalog.base_items
    )

    assert missing == []
    for item_id in _collect_reward_values("loot_queue"):
        item = item_factory.generate(ItemGenerationRequestDTO(base_id=item_id, source="scenario:awakening_rift"))
        assert item.base_id == item_id


def test_awakening_rift_reward_skills_exist_in_skill_catalog() -> None:
    skill_catalog = SkillCatalogService()

    missing = sorted(
        skill_key for skill_key in _collect_reward_values("skills_queue") if skill_catalog.get(skill_key) is None
    )

    assert missing == []


def test_awakening_rift_first_weapon_line_grants_only_weapon_mastery_and_sets_grip_family() -> None:
    expected = {
        "take_hammer": ("push:warhammer", ["push:skill_macing"], "'two_handed'"),
        "take_axe": ("push:battle_axe", ["push:skill_macing"], "'one_handed_simple'"),
        "take_katana": ("push:katana", ["push:skill_swords"], "'two_handed'"),
        "take_dagger": ("push:dagger", ["push:skill_fencing"], "'dagger'"),
        "take_staff": ("push:quarterstaff", ["push:skill_polearms"], "'two_handed'"),
        "take_sword": ("push:sword", ["push:skill_swords"], "'sword'"),
    }

    for action_id, (loot, skills, grip_family) in expected.items():
        action = _find_action("30_weapon_rewards.json", action_id)
        math = action["math"]

        assert math["loot_queue"] == loot
        assert math["skills_queue"] == skills
        assert math["grip_family"] == grip_family
        assert "is_two_handed" not in math
        assert "needs_offhand_weapon" not in math


def test_awakening_rift_second_reward_router_uses_precise_grip_family() -> None:
    router = _find_node("60_offhand_rewards.json", "resonance_logic_02")["actions"][0]

    assert router["branching"] == [
        {"condition": "grip_family == 'dagger'", "to_node": "choice_dagger_offhand"},
        {"condition": "grip_family == 'sword'", "to_node": "choice_sword_offhand"},
        {"condition": "grip_family == 'one_handed_simple'", "to_node": "choice_simple_onehand"},
        {"condition": "grip_family == 'two_handed'", "to_node": "choice_two_handed_support"},
        {"condition": "default", "to_node": "choice_two_handed_support"},
    ]


def test_awakening_rift_second_reward_paths_match_combat_skill_model() -> None:
    assert _find_action("60_offhand_rewards.json", "take_shield")["math"]["skills_queue"] == [
        "push:skill_parrying",
        "push:skill_shield_mastery",
    ]
    assert _find_action("60_offhand_rewards.json", "take_shield_simple")["math"]["skills_queue"] == [
        "push:skill_parrying",
        "push:skill_shield_mastery",
    ]
    assert _find_action("60_offhand_rewards.json", "take_buckler")["math"]["skills_queue"] == [
        "push:skill_parrying",
    ]
    assert _find_action("60_offhand_rewards.json", "take_buckler_simple")["math"]["skills_queue"] == [
        "push:skill_parrying",
    ]
    assert _find_action("60_offhand_rewards.json", "take_second_dagger")["math"]["skills_queue"] == [
        "push:skill_dual_wield",
    ]
    assert _find_action("60_offhand_rewards.json", "take_main_gauche")["math"]["skills_queue"] == [
        "push:skill_dual_wield",
        "push:skill_parrying",
    ]
    assert _find_action("60_offhand_rewards.json", "take_offhand_dagger")["math"]["skills_queue"] == [
        "push:skill_dual_wield",
    ]
    assert _find_action("60_offhand_rewards.json", "take_belt")["math"]["skills_queue"] == [
        "push:skill_one_handed",
    ]
    assert _find_action("60_offhand_rewards.json", "take_belt_twohand")["math"]["skills_queue"] == [
        "push:skill_two_handed",
    ]
    assert _find_action("60_offhand_rewards.json", "take_amulet")["math"]["skills_queue"] == [
        "push:skill_two_handed",
    ]


def test_awakening_rift_final_armor_rewards_grant_mvp_sets_plus_garments() -> None:
    expected = {
        "take_plate": (
            {
                "push:helmet",
                "push:plate_chest",
                "push:gauntlets",
                "push:greaves",
            },
            "push:skill_heavy_armor",
        ),
        "take_scale": (
            {
                "push:helmet",
                "push:plate_chest",
                "push:gauntlets",
                "push:greaves",
            },
            "push:skill_heavy_armor",
        ),
        "take_robe": (
            {
                "push:hood",
                "push:leather_armor",
                "push:soft_bracers",
                "push:scout_leggings",
            },
            "push:skill_light_armor",
        ),
        "take_leather": (
            {
                "push:hood",
                "push:leather_armor",
                "push:soft_bracers",
                "push:scout_leggings",
            },
            "push:skill_light_armor",
        ),
        "take_chainmail": (
            {
                "push:leather_cap",
                "push:jerkin",
                "push:reinforced_gloves",
                "push:breeches",
            },
            "push:skill_medium_armor",
        ),
        "take_brigandine": (
            {
                "push:leather_cap",
                "push:jerkin",
                "push:reinforced_gloves",
                "push:breeches",
            },
            "push:skill_medium_armor",
        ),
    }

    removed_armor_rewards = {
        "push:robe",
        "push:sandals",
        "push:boots",
        "push:scale_mail",
        "push:chainmail",
        "push:brigandine",
    }

    for action_id, (armor_set, skill_key) in expected.items():
        action = _find_action("90_armor_rewards.json", action_id)
        loot = set(action["math"]["loot_queue"])

        assert armor_set <= loot
        assert "push:travel_boots" in loot
        assert loot.isdisjoint(removed_armor_rewards)
        assert action["math"]["skills_queue"] == [skill_key]


def _collect_reward_values(queue_key: str) -> set[str]:
    values: set[str] = set()
    for path in sorted((QUEST_DIR / "nodes").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        _walk(data, queue_key, values)
    return values


def _walk(value: Any, queue_key: str, values: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == queue_key:
                values.update(_parse_queue_value(child))
            else:
                _walk(child, queue_key, values)
    elif isinstance(value, list):
        for child in value:
            _walk(child, queue_key, values)


def _parse_queue_value(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_strip_push(value)}
    if isinstance(value, list):
        return {_strip_push(item) for item in value if isinstance(item, str)}
    return set()


def _strip_push(value: str) -> str:
    return value.removeprefix("push:")


def _find_action(filename: str, action_id: str) -> dict[str, Any]:
    data = json.loads((QUEST_DIR / "nodes" / filename).read_text(encoding="utf-8"))
    for node in data:
        for action in node.get("actions", []):
            if action.get("action_id") == action_id:
                return action
    raise AssertionError(f"Action {action_id!r} not found in {filename}")


def _find_node(filename: str, node_key: str) -> dict[str, Any]:
    data = json.loads((QUEST_DIR / "nodes" / filename).read_text(encoding="utf-8"))
    for node in data:
        if node.get("node_key") == node_key:
            return node
    raise AssertionError(f"Node {node_key!r} not found in {filename}")

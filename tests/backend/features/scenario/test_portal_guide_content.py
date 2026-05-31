from __future__ import annotations

import json
from pathlib import Path

RESOURCE_DIR = Path("src/backend/features/scenario/resources/json/portal_guide_dialogue")


def test_portal_guide_dialogue_hub_is_repeatable_npc_topic_list() -> None:
    master = json.loads((RESOURCE_DIR / "master.json").read_text(encoding="utf-8"))
    nodes = _nodes_by_key()

    assert master["quest_key"] == "portal_guide_dialogue"
    assert master["npc_key"] == "portal_pad_guide"
    assert master["start_node_id"] == "guide_memory_entry"

    hub_actions = {action["action_id"]: action for action in nodes["guide_dialogue_hub"]["actions"]}
    assert hub_actions["ask_first_death_again"]["to_node"] == "death_return_greeting"
    assert hub_actions["ask_first_death_again"]["condition"] == "npc_flag_first_death_dialogue_seen == 1"
    assert "enter_portal" not in hub_actions


def test_portal_guide_starts_from_first_contact_memory() -> None:
    nodes = _nodes_by_key()
    router = nodes["guide_memory_entry"]["actions"][0]

    assert router["action_id"] == "auto"
    assert router["branching"] == [
        {"condition": "npc_counter_first_contact_resistance >= 1", "to_node": "memory_intro_resistant"},
        {"condition": "npc_counter_first_contact_curiosity >= 2", "to_node": "memory_intro_curious"},
        {"condition": "npc_counter_first_contact_compliance >= 1", "to_node": "memory_intro_compliant"},
        {"condition": "default", "to_node": "guide_dialogue_hub"},
    ]

    assert "подняться" in nodes["memory_intro_resistant"]["text"]
    assert "вопрос" in nodes["memory_intro_curious"]["text"]
    assert "протокол" in nodes["memory_intro_compliant"]["text"]
    for node_key in ("memory_intro_resistant", "memory_intro_curious", "memory_intro_compliant"):
        assert nodes[node_key]["actions"] == [
            {
                "action_id": "continue",
                "label": "Продолжить разговор",
                "icon": "default",
                "to_node": "guide_dialogue_hub",
            }
        ]


def test_portal_guide_nodes_use_overseer_avatar() -> None:
    for node in _nodes_by_key().values():
        if node.get("speaker") == "portal_pad_guide":
            assert node.get("avatar") == "/static/images/scenarios/overseer.webp"


def test_portal_guide_uses_first_quest_visible_name() -> None:
    nodes = _nodes_by_key()

    assert nodes["guide_dialogue_hub"]["display_name"] == "Оценщик"
    assert "Проводник Круга" not in json.dumps(nodes, ensure_ascii=False)


def test_portal_guide_first_death_branch_explains_mvp_death_rules_without_full_lore_dump() -> None:
    nodes = _nodes_by_key()
    branch_text = "\n".join(
        nodes[node_key]["text"]
        for node_key in [
            "death_return_greeting",
            "death_items_lost",
            "death_items_kept",
            "settlers_witnessed",
        ]
    )

    assert "грязными" in branch_text
    assert "круг еще не признал их твоими" in branch_text
    assert "То, что уже было признано твоим" in branch_text
    assert "полгода назад" in branch_text
    assert "Просто отметки выживших" in branch_text
    assert "хозяина этого места" not in branch_text

    finalize = nodes["final_first_death_lesson"]["metadata"]["finalize"]
    effects = finalize["effects"]
    assert finalize["target_state"] == "exploration"
    assert any(effect.get("flag") == "first_death_dialogue_seen" for effect in effects)
    assert any(effect.get("counter") == "death_dialogues" for effect in effects)


def _nodes_by_key() -> dict[str, dict]:
    nodes = []
    for path in (RESOURCE_DIR / "nodes").glob("*.json"):
        nodes.extend(json.loads(path.read_text(encoding="utf-8")))
    return {node["node_key"]: node for node in nodes}

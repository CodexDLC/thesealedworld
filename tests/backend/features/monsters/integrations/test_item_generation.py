import pytest

from src.backend.features.items.dto.instance import RuntimeItemProjectionDTO
from src.backend.features.monsters.integrations.item_generation import (
    build_member_items_projection,
    build_monster_item_request,
    to_item_generation_request,
    to_item_generation_requests,
)


@pytest.mark.unit
def test_build_monster_item_request_for_natural_equipment_creates_item_runtime_order() -> None:
    monster_request = build_monster_item_request(
        owner_key="member_0",
        family_id="rat_swarm",
        member_role="minion",
        member_tier=1,
        slot="main_hand",
        natural_key="rat_bite_claws",
        seed="clan-1/member-0/main",
    )

    item_request = to_item_generation_request(monster_request)

    assert item_request.generation_mode == "runtime"
    assert item_request.base_id == "knife"  # transmog: rat_bite_claws → knife (player item)
    assert item_request.target_slot == "main_hand"
    assert item_request.runtime_metadata["owner_key"] == "member_0"
    assert item_request.runtime_metadata["natural_key"] == "rat_bite_claws"
    assert item_request.item_grade == "common"
    assert item_request.affix_profile == "monster_equipment_4slot"
    assert item_request.affix_count == 4
    assert item_request.affix_step_count == 3
    assert "off_hand_accuracy" not in item_request.allowed_affix_ids
    assert {"natural_weapon", "rat"} <= set(item_request.extra_narrative_tags)
    assert item_request.origin_ref is not None
    assert item_request.origin_ref.seed == "clan-1/member-0/main"


@pytest.mark.unit
def test_build_monster_item_request_keeps_off_hand_accuracy_slot_scoped() -> None:
    monster_request = build_monster_item_request(
        owner_key="member_0",
        family_id="rat_swarm",
        member_role="veteran",
        member_tier=2,
        slot="off_hand",
        natural_key="rat_left_claws",
    )

    item_request = to_item_generation_request(monster_request)

    assert item_request.base_id == "dagger"
    assert item_request.target_slot == "off_hand"
    assert item_request.item_grade == "uncommon"
    assert item_request.affix_profile == "monster_equipment_4slot"
    assert item_request.affix_count == 4
    assert "off_hand_accuracy" in item_request.allowed_affix_ids


@pytest.mark.unit
def test_build_monster_item_request_maps_natural_jewelry_to_accessory_order() -> None:
    monster_request = build_monster_item_request(
        owner_key="member_0",
        family_id="rat_swarm",
        member_role="elite",
        member_tier=3,
        slot="amulet",
        natural_key="rat_plague_gland",
    )

    item_request = to_item_generation_request(monster_request)

    assert monster_request.item_kind == "accessory"
    assert item_request.base_id == "amulet"
    assert item_request.target_slot == "amulet"
    assert item_request.source_context["item_kind"] == "accessory"
    assert item_request.item_grade == "rare"
    assert item_request.affix_profile == "monster_equipment_4slot"
    assert item_request.affix_count == 4
    assert {"natural_jewelry", "rat"} <= set(item_request.extra_narrative_tags)


@pytest.mark.unit
def test_build_monster_item_request_maps_wolf_guard_natural_key_to_shield_order() -> None:
    monster_request = build_monster_item_request(
        owner_key="member_0",
        family_id="wolf_pack",
        member_role="boss",
        member_tier=4,
        slot="off_hand",
        natural_key="wolf_bone_shoulders",
    )

    item_request = to_item_generation_request(monster_request)

    assert monster_request.item_kind == "shield"
    assert item_request.base_id == "shield"
    assert item_request.target_slot == "off_hand"
    assert item_request.source_context["item_kind"] == "shield"
    assert {"natural_shield", "wolf", "guard"} <= set(item_request.extra_narrative_tags)


@pytest.mark.unit
def test_to_item_generation_requests_preserves_batch_order() -> None:
    requests = [
        build_monster_item_request(
            owner_key="member_0",
            family_id="wolf_pack",
            member_role="minion",
            member_tier=0,
            slot="main_hand",
            natural_key="wolf_bite_claws",
        ),
        build_monster_item_request(
            owner_key="member_0",
            family_id="wolf_pack",
            member_role="minion",
            member_tier=0,
            slot="chest_armor",
            natural_key="wolf_hide",
        ),
    ]

    item_requests = to_item_generation_requests(requests)

    assert [request.base_id for request in item_requests] == ["rapier", "leather_armor"]  # transmog player items
    assert [request.target_slot for request in item_requests] == ["main_hand", "chest_armor"]


@pytest.mark.unit
def test_build_member_items_projection_groups_runtime_items_by_owner() -> None:
    first = RuntimeItemProjectionDTO(
        item_id="item-1",
        owner_key="member_0",
        base_id="dagger",
        item_type="weapon",
        slot="main_hand",
        combat={"power": 3, "bonuses": {"main_hand_accuracy": "+0.01"}},
        generation={"item_grade": "common", "affix_profile": "monster_equipment_4slot", "rarity_tier": 1},
    )
    second = RuntimeItemProjectionDTO(
        item_id="item-2",
        owner_key="member_1",
        base_id="dagger",
        item_type="weapon",
        slot="main_hand",
        combat={"power": 3},
        generation={"item_grade": "common", "affix_profile": "monster_equipment_4slot", "rarity_tier": 1},
    )

    projection = build_member_items_projection([first, second], owner_key="member_0")

    assert projection.layout.equipment == {"main_hand": "item-1"}
    assert set(projection.by_id) == {"item-1"}
    assert projection.by_id["item-1"]["combat"]["bonuses"] == {"main_hand_accuracy": "+0.01"}

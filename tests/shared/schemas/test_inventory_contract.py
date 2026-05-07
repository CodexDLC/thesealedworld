from src.shared.enums.item_enums import EquippedSlot, ItemType, QuickSlot
from src.shared.schemas.inventory import (
    InventoryActionRequestDTO,
    InventoryContainerRowDTO,
    InventoryDetailLineDTO,
    InventoryItemDetailsDTO,
    InventoryRequirementDTO,
    InventoryWindowDTO,
)


def test_inventory_contract_uses_clean_slot_model_without_feet_armor() -> None:
    assert EquippedSlot.FEETWEAR.value == "feetwear"
    assert "feet_armor" not in {slot.value for slot in EquippedSlot}
    assert QuickSlot.BELT_SLOT_1.value == "belt_slot_1"
    assert QuickSlot.BELT_SLOT_8.value == "belt_slot_8"
    assert ItemType.GARMENT.value == "garment"
    assert ItemType.QUEST.value == "quest"


def test_inventory_action_contract_accepts_belt_actions() -> None:
    dto = InventoryActionRequestDTO(
        char_id=7,
        action="move_to_belt",
        item_id="potion-1",
        slot_id="belt_slot_1",
    )

    assert dto.action == "move_to_belt"


def test_inventory_window_contract_state_is_shared_v1() -> None:
    fields = InventoryWindowDTO.model_fields

    assert fields["contract_state"].default == "SHARED_INVENTORY_CONTRACT_V1"
    assert "body_zones" in fields
    assert "quick_slots" in fields
    assert "visible_rows" in fields


def test_inventory_container_rows_expose_valid_equip_targets() -> None:
    assert "valid_slots" in InventoryContainerRowDTO.model_fields


def test_inventory_tooltip_contract_is_structured_and_html_free() -> None:
    details = InventoryItemDetailsDTO(
        item_id="item-1",
        name="Archivist Ring",
        item_type="accessory",
        rarity="rare",
        rarity_tier=3,
        rarity_label="Rare",
        description="Plain text only.",
        flavor="No HTML leaves the backend.",
        details=[InventoryDetailLineDTO(label="Memory", value="+3", tone="positive")],
        comparison=[InventoryDetailLineDTO(label="Memory", value="+1", tone="positive", delta=1)],
        requirements=[InventoryRequirementDTO(label="INT", value="14", current="12", met=False)],
    )

    dumped = details.model_dump_json()
    assert details.rarity_tier == 3
    assert details.details[0].tone == "positive"
    assert details.requirements[0].met is False
    assert "<" not in dumped
    assert "ic-stat-val" not in dumped

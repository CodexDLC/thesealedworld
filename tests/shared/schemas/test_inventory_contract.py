from src.shared.enums.item_enums import EquippedSlot, ItemType, QuickSlot
from src.shared.schemas.inventory import InventoryActionRequestDTO, InventoryWindowDTO


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

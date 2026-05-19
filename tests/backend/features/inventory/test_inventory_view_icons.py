from src.backend.features.inventory.services.view import InventoryViewService
from src.shared.schemas.inventory import InventoryRuntimeItemDTO


def _item(base_id: str, item_type: str, *, slot: str, tags: list[str] | None = None) -> InventoryRuntimeItemDTO:
    return InventoryRuntimeItemDTO(
        item_id=f"item:{base_id}",
        base_id=base_id,
        item_type=item_type,
        slot=slot,
        valid_slots=[slot],
        name=base_id,
        tags=tags or [],
    )


def test_inventory_view_uses_specific_leg_armor_icons() -> None:
    service = InventoryViewService()

    assert service._icon_key(_item("fur_pants", "garment", slot="legs_garment")) == "legwear"
    assert service._icon_key(_item("scout_leggings", "armor", slot="legs_armor")) == "legs_light"
    assert service._icon_key(_item("breeches", "armor", slot="legs_armor")) == "legs_medium"
    assert service._icon_key(_item("greaves", "armor", slot="legs_armor")) == "legs_heavy"


def test_inventory_view_splits_polearm_family_icons() -> None:
    service = InventoryViewService()

    assert service._icon_key(_item("spear", "weapon", slot="main_hand", tags=["spear", "polearm"])) == "weapon_spear"
    assert service._icon_key(_item("pike", "weapon", slot="two_hand", tags=["pike", "polearm"])) == "weapon_pike"
    assert service._icon_key(_item("halberd", "weapon", slot="two_hand", tags=["halberd", "polearm"])) == "weapon_halberd"
    assert service._icon_key(_item("quarterstaff", "weapon", slot="two_hand", tags=["staff", "polearm"])) == "weapon_staff"
    assert service._icon_key(_item("trident", "weapon", slot="main_hand", tags=["trident", "polearm"])) == "weapon_trident"


def test_inventory_view_uses_distinct_resource_icons_by_category() -> None:
    service = InventoryViewService()

    assert service._resource_icon_key("res_iron_ore", item_type="resource") == "resource_ore"
    assert service._resource_icon_key("res_oak_log", item_type="resource") == "resource_wood"
    assert service._resource_icon_key("res_plant_fiber", item_type="resource") == "resource_fiber"
    assert service._resource_icon_key("res_torn_pelt", item_type="resource") == "resource_hide"
    assert service._resource_icon_key("currency_dust", item_type="currency") == "resource_currency"

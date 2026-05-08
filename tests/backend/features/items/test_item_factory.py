import pytest

from src.backend.features.items.dto.instance import ItemGenerationRequestDTO
from src.backend.features.items.runtime.item_factory import ItemFactory


@pytest.mark.unit
def test_item_factory_generates_combat_ready_item_spec():
    item = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="warhammer",
            material_id="mat_iron_ingot",
            rarity_tier=1,
            affix_bundle_ids=["soldier"],
            source="scenario:awakening_rift",
        )
    )

    assert item.base_id == "warhammer"
    assert item.material_id == "mat_iron_ingot"
    assert item.rarity == "uncommon"
    assert item.power > 0
    assert item.slot == "two_hand"
    assert item.implicit_bonuses["accuracy_penalty"] == pytest.approx(0.288)
    assert item.implicit_bonuses["main_hand_penetration"] == pytest.approx(0.264)
    assert item.implicit_bonuses["evasion_penalty"] == pytest.approx(-0.12)
    assert "phys_dmg_flat" not in item.bonuses
    assert "physical_damage_bonus" in item.bonuses
    assert item.metadata["source"] == "scenario:awakening_rift"

import pytest

from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemPlacementRefDTO
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.models import ItemInstance, ItemPlacement, ItemTransaction
from src.backend.features.items.repositories import ItemInstanceRepository


class FakeScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class FakeSession:
    def __init__(self, scalar_values=None):
        self.added = []
        self.scalar_values = scalar_values or []
        self.flushed = False

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flushed = True

    async def scalars(self, _stmt):
        return FakeScalarResult(self.scalar_values)


@pytest.mark.unit
async def test_create_mechanical_persists_current_and_max_durability():
    session = FakeSession()
    repo = ItemInstanceRepository(session)

    await repo.create_mechanical(
        GeneratedItemDTO(
            instance_id="item-1",
            template_id="warhammer",
            item_type="weapon",
            rarity="common",
            rarity_tier=0,
            name="Warhammer",
            description="A heavy hammer.",
            base_id="warhammer",
            power=5,
            durability_max=45,
            slot="two_hand",
            mechanics={
                "material": {"material_id": "mat_iron_ingot", "tier_mult": 1.0, "tags": []},
                "affixes": [{"affix_id": "crit_chance", "value": 0.03, "source": "single:combat_offense"}],
                "sockets": [],
            },
        ),
        ItemPlacementRefDTO(holder_type="character", holder_id="42", storage_type="equipped", slot="two_hand"),
        text_status="not_requested",
    )

    instance = next(value for value in session.added if isinstance(value, ItemInstance))

    assert instance.mechanics["durability_current"] == 45
    assert instance.mechanics["durability_max"] == 45
    assert instance.mechanics["material"]["material_id"] == "mat_iron_ingot"
    assert instance.mechanics["affixes"][0]["affix_id"] == "crit_chance"


@pytest.mark.unit
def test_persistence_integration_restores_canonical_mechanics():
    instance = ItemInstance(
        id="item-1",
        base_id="warhammer",
        item_type="weapon",
        rarity="common",
        rarity_tier=0,
        lifecycle_status="ready",
        text_status="not_requested",
        name="Warhammer",
        description="A heavy hammer.",
        mechanics={
            "template_id": "warhammer:mat_iron_ingot:common",
            "slot": "two_hand",
            "valid_slots": ["two_hand"],
            "power": 5,
            "durability_max": 45,
            "damage_spread": 0.1,
            "implicit_bonuses": {},
            "bonuses": {},
            "triggers": [],
            "material": {"material_id": "mat_iron_ingot", "tier_mult": 1.0, "tags": []},
            "affixes": [{"affix_id": "crit_chance", "value": 0.03, "source": "single:combat_offense"}],
            "sockets": [],
        },
        appearance={},
        generation={"material_id": "mat_iron_ingot", "affix_bundle_ids": [], "narrative_tags": []},
        metadata_={},
    )

    dto = ItemPersistenceIntegration(FakeSession())._dto_from_instance(instance)

    assert dto.mechanics["material"]["material_id"] == "mat_iron_ingot"
    assert dto.mechanics["affixes"][0]["affix_id"] == "crit_chance"


@pytest.mark.unit
async def test_transfer_character_items_to_system_moves_all_character_placements_and_records_transactions():
    placement = ItemPlacement(
        item_id="item-1",
        holder_type="character",
        holder_id="42",
        storage_type="equipped",
        slot="two_hand",
        position_index=3,
        locked_by="combat",
    )
    session = FakeSession([placement])
    repo = ItemInstanceRepository(session)

    transferred_count = await repo.transfer_character_items_to_system(42)

    transaction = next(value for value in session.added if isinstance(value, ItemTransaction))
    assert transferred_count == 1
    assert placement.holder_type == "system"
    assert placement.holder_id == "deleted_character:42"
    assert placement.storage_type == "deleted_character_recovery"
    assert placement.slot is None
    assert placement.position_index is None
    assert placement.locked_by is None
    assert transaction.item_id == "item-1"
    assert transaction.from_holder_type == "character"
    assert transaction.from_holder_id == "42"
    assert transaction.from_storage_type == "equipped"
    assert transaction.to_holder_type == "system"
    assert transaction.to_holder_id == "deleted_character:42"
    assert transaction.to_storage_type == "deleted_character_recovery"
    assert transaction.reason == "character_deleted"

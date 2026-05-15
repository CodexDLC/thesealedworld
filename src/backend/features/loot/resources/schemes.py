from __future__ import annotations

from src.backend.features.loot.resources.types import LootEntry, LootScheme

# ---------------------------------------------------------------------------
# Scheme registry
# Key = loot_scheme_id referenced from monster schema (monster.loot_scheme_id)
# ---------------------------------------------------------------------------

LOOT_SCHEMES: dict[str, LootScheme] = {
    "beast_tier1": LootScheme(
        id="beast_tier1",
        entries=[
            LootEntry(template_id="hide_rough", item_type="resource", tier=1, drop_chance=0.80, amount_range=(1, 3)),
            LootEntry(template_id="bone_fragment", item_type="resource", tier=1, drop_chance=0.60, amount_range=(1, 2)),
            LootEntry(template_id="beast_fang", item_type="resource", tier=1, drop_chance=0.30, amount_range=(1, 1)),
        ],
    ),
    "beast_tier2": LootScheme(
        id="beast_tier2",
        entries=[
            LootEntry(template_id="hide_cured", item_type="resource", tier=2, drop_chance=0.75, amount_range=(1, 2)),
            LootEntry(template_id="bone_fragment", item_type="resource", tier=2, drop_chance=0.50, amount_range=(2, 4)),
            LootEntry(template_id="beast_claw", item_type="resource", tier=2, drop_chance=0.40, amount_range=(1, 1)),
            LootEntry(
                template_id="dagger_crude",
                item_type="equipment",
                tier=2,
                drop_chance=0.10,
                rarity_pool=("common", "uncommon"),
            ),
        ],
    ),
    "humanoid_bandit": LootScheme(
        id="humanoid_bandit",
        entries=[
            LootEntry(template_id="coin_copper", item_type="currency", tier=1, drop_chance=0.90, amount_range=(5, 20)),
            LootEntry(template_id="cloth_scrap", item_type="resource", tier=1, drop_chance=0.60, amount_range=(1, 3)),
            LootEntry(
                template_id="sword_iron",
                item_type="equipment",
                tier=1,
                drop_chance=0.20,
                rarity_pool=("common",),
            ),
            LootEntry(
                template_id="armor_leather",
                item_type="equipment",
                tier=1,
                drop_chance=0.15,
                rarity_pool=("common",),
            ),
        ],
    ),
    "humanoid_mage": LootScheme(
        id="humanoid_mage",
        entries=[
            LootEntry(template_id="coin_copper", item_type="currency", tier=1, drop_chance=0.80, amount_range=(10, 40)),
            LootEntry(
                template_id="mana_crystal_shard", item_type="resource", tier=2, drop_chance=0.50, amount_range=(1, 2)
            ),
            LootEntry(
                template_id="staff_gnarled",
                item_type="equipment",
                tier=2,
                drop_chance=0.15,
                rarity_pool=("common", "uncommon"),
            ),
        ],
    ),
    "construct_golem": LootScheme(
        id="construct_golem",
        entries=[
            LootEntry(template_id="stone_chunk", item_type="resource", tier=2, drop_chance=0.90, amount_range=(2, 5)),
            LootEntry(template_id="iron_scrap", item_type="resource", tier=2, drop_chance=0.70, amount_range=(1, 3)),
            LootEntry(template_id="core_fragment", item_type="resource", tier=3, drop_chance=0.20, amount_range=(1, 1)),
        ],
    ),
    "default": LootScheme(
        id="default",
        entries=[
            LootEntry(template_id="coin_copper", item_type="currency", tier=1, drop_chance=0.50, amount_range=(1, 5)),
        ],
    ),
}

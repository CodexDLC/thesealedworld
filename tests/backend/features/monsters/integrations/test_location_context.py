from src.backend.features.monsters.integrations.location_context import MonsterLocationContextIntegration


class FakeWorldLocations:
    async def get_location(self, loc_id: str) -> dict:
        return {
            "loc_id": loc_id,
            "tags": ["city_ruins", "mana_leak"],
            "flags": {"threat_tier": 1},
            "anchor_influence": {"tier": 2, "threat": 0.5, "tags": ["cursed_ground"]},
            "zone_id": "D4_0_0",
            "world_zone": {
                "id": "D4_0_0",
                "region_id": "D4",
                "biome_id": "city_ruins",
                "tier": 0,
                "flags": {},
            },
        }


async def test_location_context_reads_world_zone_projection() -> None:
    context = await MonsterLocationContextIntegration(FakeWorldLocations()).get_location_context("45_45")  # type: ignore[arg-type]

    assert context.loc_id == "45_45"
    assert context.zone_id == "D4_0_0"
    assert context.biome_id == "city_ruins"
    assert context.tier == 2
    assert context.danger == 0.5
    assert context.tags == ["city_ruins", "mana_leak", "cursed_ground"]

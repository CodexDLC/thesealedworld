import pytest

from src.backend.features.monsters.services.habitat_clan_pool_materialization_service import (
    HabitatClanPoolMaterializationResult,
    HabitatScopeConfig,
)
from src.backend.features.rift.resources.loader import RiftResourceLoader
from src.backend.features.rift.services.population_bootstrap import RiftPopulationBootstrapService


class FakeMaterializer:
    def __init__(self) -> None:
        self.configs: list[HabitatScopeConfig] = []

    async def ensure_scope_pool(self, config: HabitatScopeConfig) -> HabitatClanPoolMaterializationResult:
        self.configs.append(config)
        policy = config.clan_pool_policy
        return HabitatClanPoolMaterializationResult(
            scopes=1,
            pool_entries=len(policy.primary) + len(policy.secondary),
            clans=len(policy.primary) + len(policy.secondary),
        )


@pytest.mark.unit
async def test_rift_population_bootstrap_materializes_habitat_clan_pool_contract() -> None:
    materializer = FakeMaterializer()
    service = RiftPopulationBootstrapService(
        loader=RiftResourceLoader(),
        materializer=materializer,  # type: ignore[arg-type]
    )

    result = await service.ensure_static_population(["starter_rift"])

    assert result.rifts == 1
    assert result.family_slots == 2
    assert result.clans == 2
    assert result.pruned_clans == 0
    assert result.bindings == {}
    assert len(materializer.configs) == 1

    config = materializer.configs[0]
    assert config.scope_type == "rift"
    assert config.scope_id == "starter_rift"
    assert config.habitat.model_dump(mode="json") == {
        "biome": "broken_road",
        "keys": ["road_tract", "scavenger_camp"],
    }
    assert [entry.family_id for entry in config.clan_pool_policy.primary] == ["goblin_tribe"]
    assert [entry.family_id for entry in config.clan_pool_policy.secondary] == ["rat_swarm"]
    assert config.source_meta is not None
    assert config.source_meta["setting_key"] == "starter_rift"
    assert set(config.source_meta["clan_flavors"]) == {"goblin_tribe", "rat_swarm"}

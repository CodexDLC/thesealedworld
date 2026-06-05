import pytest

from src.backend.features.monsters.services.world_population_service import WorldMonsterPopulationService


async def test_world_population_service_is_removed() -> None:
    service = WorldMonsterPopulationService(object())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="HabitatClanPoolMaterializationService"):
        await service.ensure_population_for_nodes([])

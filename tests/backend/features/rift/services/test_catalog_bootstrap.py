from __future__ import annotations

import inspect
from typing import Any

import pytest

from src.backend.core.containers.game import GameFeatureContainer
from src.backend.features.rift.resources import RiftResourceLoader
from src.backend.features.rift.services.catalog_bootstrap import RiftCatalogBootstrapService


@pytest.mark.unit
async def test_rift_catalog_bootstrap_syncs_setting_and_node_pool_from_fixtures() -> None:
    settings = _FakeRepository()
    nodes = _FakeRepository()

    result = await RiftCatalogBootstrapService(
        loader=RiftResourceLoader(),
        setting_repository=settings,
        node_pool_repository=nodes,
    ).sync_fixtures(["starter_rift"])

    assert result.settings == 1
    assert result.nodes == 15

    setting = settings.upserts[0]
    assert setting.setting_key == "starter_rift"
    assert setting.setting_hash == "v1_starter_rift_broken_caravan"
    assert setting.title == "Рваный тракт"
    assert setting.biome_id == "broken_road"
    assert setting.normalized_tags == sorted(
        [
        "starter_rift",
        "tier_1_rift",
        "broken_caravan",
        "roadside_camp",
        "goblin_scavengers",
        "rift_scavenger_beasts",
        ]
    )
    assert setting.profile_json["summary"].startswith("Стартовый лорный разлом")
    assert setting.generation_rules_json["assembly_options"]["default_seed"] == "starter-rift-dev"
    assert setting.text_vocabulary_json["transition_combat"]

    first_node = nodes.upserts[0]
    assert first_node.pool_node_id == "starter_rift:001_broken_milestone"
    assert first_node.setting_key == "starter_rift"
    assert first_node.pool_node_key == "001_broken_milestone"
    assert first_node.node_hash == "sr0000000001"
    assert first_node.node_role == "start"
    assert first_node.title == "Вход у разбитой вехи"
    assert "Старая дорожная веха" in first_node.description
    assert first_node.tags == ["road", "starter_rift"]
    assert first_node.role_fit == ["start", "generic"]
    assert first_node.approach_view_json["open_suffix"]
    assert first_node.transition_text_json["enter_target"] == "к разбитой вехе"
    assert first_node.generation_json["source"] == "manual"
    assert first_node.generation_json["pool_order"] == 0


@pytest.mark.unit
def test_game_feature_bootstrap_syncs_rift_catalog_before_population() -> None:
    source = inspect.getsource(GameFeatureContainer._bootstrap_world)

    assert "RiftCatalogBootstrapService" in source
    assert source.index("RiftCatalogBootstrapService") < source.index("RiftPopulationBootstrapService")


class _FakeRepository:
    def __init__(self) -> None:
        self.upserts: list[Any] = []

    async def upsert(self, value: Any) -> Any:
        self.upserts.append(value)
        return value

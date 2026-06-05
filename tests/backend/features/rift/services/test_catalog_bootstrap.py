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
    documents = _FakeCatalogDocumentRepository()

    result = await RiftCatalogBootstrapService(
        loader=RiftResourceLoader(),
        setting_repository=settings,
        node_pool_repository=nodes,
        catalog_document_repository=documents,
    ).sync_fixtures(["starter_rift"])

    assert result.settings == 1
    assert result.nodes == 15

    setting = settings.upserts[0]
    assert setting.setting_key == "starter_rift"
    assert setting.setting_hash == "v1_starter_rift_broken_caravan"
    assert setting.title == "Рваный тракт"
    assert setting.biome_id == "broken_road"
    assert setting.normalized_tags == []
    assert setting.mongo_setting_doc_id == "rift-setting:starter_rift"
    assert setting.mongo_status == "synced"
    assert documents.setting_payloads["starter_rift"]["profile"]["summary"].startswith("Стартовый лорный разлом")
    assert (
        documents.setting_payloads["starter_rift"]["generation_rules"]["assembly_options"]["default_seed"]
        == "starter-rift-dev"
    )
    assert documents.setting_payloads["starter_rift"]["text_vocabulary"]["transition_combat"]

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
    assert first_node.mongo_node_doc_id == "rift-node:starter_rift:001_broken_milestone"
    assert first_node.mongo_status == "synced"
    first_node_payload = documents.node_payloads["starter_rift:001_broken_milestone"]
    assert first_node_payload["approach_view"]["open_suffix"]
    assert first_node_payload["transition_text"]["enter_target"] == "к разбитой вехе"
    assert first_node_payload["generation"]["source"] == "manual"
    assert first_node_payload["generation"]["pool_order"] == 0


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


class _FakeCatalogDocumentRepository:
    def __init__(self) -> None:
        self.setting_payloads: dict[str, dict[str, Any]] = {}
        self.node_payloads: dict[str, dict[str, Any]] = {}

    async def upsert_setting_document(self, *, setting_key: str, payload: dict[str, Any]) -> str:
        self.setting_payloads[setting_key] = payload
        return f"rift-setting:{setting_key}"

    async def upsert_node_document(
        self,
        *,
        pool_node_id: str,
        setting_key: str,
        pool_node_key: str,
        payload: dict[str, Any],
    ) -> str:
        _ = setting_key, pool_node_key
        self.node_payloads[pool_node_id] = payload
        return f"rift-node:{pool_node_id}"


@pytest.mark.unit
async def test_game_feature_bootstrap_ai_scheduling_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.backend.core.containers.game.settings.bootstrap_ai_generation_enabled", False)
    scheduler = _FakeGenerationAIScheduler()

    scheduled = await GameFeatureContainer()._schedule_bootstrap_generation_ai(scheduler)  # type: ignore[arg-type]

    assert scheduled == 0
    assert scheduler.calls == 0


@pytest.mark.unit
async def test_game_feature_bootstrap_ai_scheduling_requires_explicit_enable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.backend.core.containers.game.settings.bootstrap_ai_generation_enabled", True)
    scheduler = _FakeGenerationAIScheduler()

    scheduled = await GameFeatureContainer()._schedule_bootstrap_generation_ai(scheduler)  # type: ignore[arg-type]

    assert scheduled == 3
    assert scheduler.calls == 1


class _FakeGenerationAIScheduler:
    def __init__(self) -> None:
        self.calls = 0

    async def schedule_pending_task_ids(self) -> int:
        self.calls += 1
        return 3

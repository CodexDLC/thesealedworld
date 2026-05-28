from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from loguru import logger as log

from src.backend.features.rift.runtime.generation import build_population_context
from src.backend.infrastructure.rift.models import RiftNodePoolRecord, RiftSetting

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.rift.dto import RiftPoolNodeDTO
    from src.backend.features.rift.resources.loader import RiftResourceLoader


class _SettingRepository(Protocol):
    async def upsert(self, setting: RiftSetting) -> RiftSetting: ...


class _NodePoolRepository(Protocol):
    async def upsert(self, node: RiftNodePoolRecord) -> RiftNodePoolRecord: ...


@dataclass(frozen=True, slots=True)
class RiftCatalogBootstrapResult:
    settings: int
    nodes: int


class RiftCatalogBootstrapService:
    """Synchronizes authored rift fixture catalog data into SQL lookup tables."""

    def __init__(
        self,
        *,
        loader: RiftResourceLoader,
        setting_repository: _SettingRepository,
        node_pool_repository: _NodePoolRepository,
    ) -> None:
        self.loader = loader
        self.setting_repository = setting_repository
        self.node_pool_repository = node_pool_repository

    async def sync_fixtures(self, setting_keys: Sequence[str] | None = None) -> RiftCatalogBootstrapResult:
        keys = list(setting_keys or self.loader.list_setting_keys())
        settings_count = 0
        nodes_count = 0

        for setting_key in keys:
            setting = self.loader.load_setting(setting_key)
            await self.setting_repository.upsert(_setting_from_fixture(setting))
            settings_count += 1

            for node in self.loader.load_node_pool(setting_key).values():
                await self.node_pool_repository.upsert(_node_from_fixture(setting_key=setting_key, node=node))
                nodes_count += 1

        log.bind(setting_count=settings_count, node_count=nodes_count).info("RiftCatalogFixturesSynced")
        return RiftCatalogBootstrapResult(settings=settings_count, nodes=nodes_count)


def _setting_from_fixture(setting: dict[str, Any]) -> RiftSetting:
    population = build_population_context(setting)
    profile = dict(setting.get("profile") or {})
    screen = dict(setting.get("screen") or {})
    return RiftSetting(
        setting_key=str(setting["setting_key"]),
        setting_hash=str(setting["setting_hash"]),
        title=str(profile.get("title") or screen.get("subtitle") or screen.get("title") or setting["setting_key"]),
        biome_id=str(population.get("biome_id") or "wasteland"),
        generation_version=int(setting.get("schema_version") or 1),
        normalized_tags=list(population.get("tags") or []),
        profile_json=profile,
        generation_rules_json={
            "source": setting.get("source"),
            "axis_schema_version": setting.get("axis_schema_version"),
            "screen": screen,
            "heart": dict(setting.get("heart") or {}),
            "assembly_options": dict(setting.get("assembly_options") or {}),
            "population_generation": dict(setting.get("population_generation") or {}),
        },
        text_vocabulary_json={
            "text_templates": dict(setting.get("text_templates") or {}),
            "encounter_vocabulary": dict(setting.get("encounter_vocabulary") or {}),
            "transition_combat": list(dict(setting.get("encounter_vocabulary") or {}).get("transition_combat") or []),
        },
        metadata_={
            "fixture_source": "rift_resource_loader",
            "sync_source": "rift_catalog_bootstrap",
        },
        source_context={
            "resource": f"{setting['setting_key']}/master.json",
        },
        schema_version=int(setting.get("schema_version") or 1),
    )


def _node_from_fixture(*, setting_key: str, node: RiftPoolNodeDTO) -> RiftNodePoolRecord:
    text = node.generated_text
    return RiftNodePoolRecord(
        pool_node_id=node.pool_node_id,
        setting_key=setting_key,
        pool_node_key=_pool_node_key(node.pool_node_id, setting_key=setting_key),
        node_hash=node.node_hex or node.pool_node_id,
        node_role=_node_role(node.role_fit),
        title=text.title,
        description=text.description,
        tags=list(node.tags),
        role_fit=list(node.role_fit),
        approach_view_json=dict(text.approach_view),
        transition_text_json=dict(text.transition_text),
        generation_json={
            "source": node.source,
            "axis_schema_version": node.axis_schema_version,
            "pool_order": node.pool_order,
            "axes": dict(node.axes),
        },
        metadata_={
            "fixture_source": "rift_resource_loader",
            "sync_source": "rift_catalog_bootstrap",
        },
        source_context={
            "resource": f"{setting_key}/nodes.json",
            "pool_node_id": node.pool_node_id,
        },
        schema_version=max(1, int(node.axis_schema_version or 1)),
    )


def _pool_node_key(pool_node_id: str, *, setting_key: str) -> str:
    prefix = f"{setting_key}:"
    if pool_node_id.startswith(prefix):
        return pool_node_id.removeprefix(prefix)
    return pool_node_id.rsplit(":", 1)[-1]


def _node_role(role_fit: list[str]) -> str:
    for role in role_fit:
        text = str(role or "").strip()
        if text:
            return text
    return "ordinary"

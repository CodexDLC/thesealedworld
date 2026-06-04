from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger as log

from src.backend.features.monsters.services.habitat_clan_pool_materialization_service import (
    HabitatClanPoolMaterializationService,
    habitat_scope_config_from_population_profile,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.rift.resources.loader import RiftResourceLoader


@dataclass(frozen=True, slots=True)
class RiftPopulationBootstrapResult:
    rifts: int
    family_slots: int
    clans: int
    pruned_clans: int
    bindings: dict[str, dict[str, dict]]


class RiftPopulationBootstrapService:
    """Creates materialized habitat clan pool rows for authored rift settings."""

    def __init__(
        self,
        *,
        loader: RiftResourceLoader,
        materializer: HabitatClanPoolMaterializationService,
    ) -> None:
        self.loader = loader
        self.materializer = materializer

    async def ensure_static_population(
        self, setting_keys: Sequence[str] | None = None
    ) -> RiftPopulationBootstrapResult:
        keys = list(setting_keys or self.loader.list_setting_keys())
        rifts_count = 0
        entries_count = 0
        clans_count = 0

        for setting_key in keys:
            setting = self.loader.load_setting(setting_key)
            population = dict(setting.get("population_generation") or {})
            if not population.get("habitat") or not population.get("clan_pool_policy"):
                continue
            config = habitat_scope_config_from_population_profile(
                scope_type="rift",
                scope_id=str(setting.get("setting_key") or setting_key),
                population_profile=population,
                default_biome=str(population.get("biome_id") or "rift"),
                tier=max(1, int(population.get("tier") or dict(setting.get("screen") or {}).get("tier") or 1)),
                source_meta={"setting_key": str(setting.get("setting_key") or setting_key)},
            )
            result = await self.materializer.ensure_scope_pool(config)
            rifts_count += result.scopes
            entries_count += result.pool_entries
            clans_count += result.clans

        log.bind(rift_count=rifts_count, entry_count=entries_count, clan_count=clans_count).info(
            "RiftHabitatClanPoolsEnsured"
        )
        return RiftPopulationBootstrapResult(
            rifts=rifts_count,
            family_slots=entries_count,
            clans=clans_count,
            pruned_clans=0,
            bindings={},
        )

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from loguru import logger as log

from src.backend.features.monsters.dto import (
    ClanPoolPolicyDTO,
    HabitatClanPoolEntryDTO,
    MonsterGenerationContext,
    MonsterHabitatDTO,
)
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.traits import select_monster_clan_traits_for_habitat
from src.backend.features.monsters.runtime.hashing import compute_clan_identity_hash, compute_habitat_hash

if TYPE_CHECKING:
    from collections.abc import Iterable

    from src.backend.features.monsters.integrations import MonsterGenerationStorage
    from src.backend.features.monsters.runtime.clan_factory import ClanFactory


@dataclass(frozen=True, slots=True)
class HabitatScopeConfig:
    scope_type: Literal["region", "rift"]
    scope_id: str
    habitat: MonsterHabitatDTO
    clan_pool_policy: ClanPoolPolicyDTO
    tier: int = 1
    source_meta: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class HabitatClanPoolMaterializationResult:
    scopes: int
    pool_entries: int
    clans: int


class HabitatClanPoolMaterializationService:
    def __init__(
        self,
        *,
        repository: MonsterGenerationStorage,
        factory: ClanFactory,
    ) -> None:
        self.repository = repository
        self.factory = factory

    async def ensure_scope_pool(self, config: HabitatScopeConfig) -> HabitatClanPoolMaterializationResult:
        clans = 0
        entries = 0
        blocked = set(config.clan_pool_policy.blocked)
        for pool_tier, policy_entries in (
            ("primary", config.clan_pool_policy.primary),
            ("secondary", config.clan_pool_policy.secondary),
        ):
            for policy_entry in policy_entries:
                family_id = policy_entry.family_id
                if not family_id or family_id in blocked:
                    continue
                family = get_family_config(family_id)
                if family is None:
                    raise ValueError(f"Unknown monster family in habitat clan pool: {family_id}")
                selected_traits = select_monster_clan_traits_for_habitat(
                    family,
                    biome_id=config.habitat.biome,
                    habitat_keys=config.habitat.keys,
                )
                selected_trait_keys = [trait.key for trait in selected_traits]
                context_hash = compute_habitat_hash(biome=config.habitat.biome, keys=config.habitat.keys)
                identity_hash = compute_clan_identity_hash(
                    family_id=family_id,
                    biome=config.habitat.biome,
                    keys=config.habitat.keys,
                    selected_trait_keys=selected_trait_keys,
                    generation_version=2,
                    resource_version=family.resource_version,
                )
                existing = await self.repository.get_clan_by_identity_hash(identity_hash)
                if existing is None:
                    context = MonsterGenerationContext(
                        zone_id=f"{config.scope_type}:{config.scope_id}",
                        biome_id=config.habitat.biome,
                        habitat=config.habitat,
                        tier=max(1, min(7, int(config.tier))),
                        tags=list(config.habitat.keys),
                        difficulty="mid",
                        context_meta={
                            "scope_type": config.scope_type,
                            "scope_id": config.scope_id,
                            "source": dict(config.source_meta or {}),
                            "clan_pool_policy": config.clan_pool_policy.model_dump(mode="json"),
                            "clan_flavor": _required_clan_flavor(config, family_id),
                        },
                    )
                    await self.factory.build_clan_template(
                        context=context,
                        family_id=family_id,
                        context_hash=context_hash,
                        identity_hash=identity_hash,
                        normalized_tags=list(config.habitat.keys),
                    )
                    clans += 1
                await self.repository.upsert_habitat_clan_pool_entry(
                    HabitatClanPoolEntryDTO(
                        scope_type=config.scope_type,
                        scope_id=config.scope_id,
                        clan_identity_hash=identity_hash,
                        family_id=family_id,
                        pool_tier=pool_tier,  # type: ignore
                        weight=policy_entry.weight,
                        enabled=True,
                        habitat=config.habitat,
                        policy_version=config.clan_pool_policy.policy_version,
                    )
                )
                entries += 1
        log.bind(
            scope_type=config.scope_type,
            scope_id=config.scope_id,
            entry_count=entries,
            created_clan_count=clans,
        ).info("HabitatClanPoolMaterialized")
        return HabitatClanPoolMaterializationResult(scopes=1, pool_entries=entries, clans=clans)

    async def ensure_scope_pools(self, configs: Iterable[HabitatScopeConfig]) -> HabitatClanPoolMaterializationResult:
        scopes = 0
        entries = 0
        clans = 0
        for config in configs:
            result = await self.ensure_scope_pool(config)
            scopes += result.scopes
            entries += result.pool_entries
            clans += result.clans
        return HabitatClanPoolMaterializationResult(scopes=scopes, pool_entries=entries, clans=clans)


def habitat_scope_config_from_population_profile(
    *,
    scope_type: Literal["region", "rift"],
    scope_id: str,
    population_profile: dict[str, Any],
    default_biome: str,
    tier: int = 1,
    source_meta: dict[str, Any] | None = None,
) -> HabitatScopeConfig:
    habitat_raw = dict(population_profile.get("habitat") or {})
    habitat = MonsterHabitatDTO.model_validate(
        {
            "biome": habitat_raw.get("biome") or default_biome,
            "keys": habitat_raw.get("keys") or [],
        }
    )
    policy_raw = dict(population_profile.get("clan_pool_policy") or {})
    policy = ClanPoolPolicyDTO.model_validate(policy_raw)
    resolved_source_meta = dict(source_meta or {})
    clan_flavors = population_profile.get("clan_flavors")
    if isinstance(clan_flavors, dict):
        resolved_source_meta["clan_flavors"] = dict(clan_flavors)
    return HabitatScopeConfig(
        scope_type=scope_type,
        scope_id=str(scope_id),
        habitat=habitat,
        clan_pool_policy=policy,
        tier=tier,
        source_meta=resolved_source_meta,
    )


def _required_clan_flavor(config: HabitatScopeConfig, family_id: str) -> dict[str, object]:
    source_meta = dict(config.source_meta or {})
    raw_flavors = source_meta.get("clan_flavors")
    flavors = dict(raw_flavors) if isinstance(raw_flavors, dict) else {}
    flavor = flavors.get(family_id)
    if not isinstance(flavor, dict):
        raise ValueError(
            "Habitat clan pool materialization requires authored clan_flavors "
            f"for family={family_id} scope={config.scope_type}:{config.scope_id}"
        )
    return dict(flavor)

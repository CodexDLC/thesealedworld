from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.traits import (
    select_monster_clan_traits_for_habitat,
    serialize_selected_trait,
)
from src.backend.features.monsters.runtime.hashing import (
    compute_clan_identity_hash,
    compute_habitat_hash,
)

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.generation import GeneratedClan, MonsterGenerationContext
    from src.backend.features.monsters.integrations import MonsterGenerationStorage
    from src.backend.features.monsters.runtime.clan_factory import ClanFactory


class EncounterMonsterService:
    def __init__(
        self,
        repository: MonsterGenerationStorage,
        factory: ClanFactory,
    ) -> None:
        self.repository = repository
        self.factory = factory

    async def prune_generated_clans_for_zone_contexts(self, expected: dict[str, set[tuple[str, str]]]) -> int:
        delete_generated_clans = getattr(self.repository, "delete_generated_clans_outside_zone_contexts", None)
        if not callable(delete_generated_clans):
            return 0
        return int(await delete_generated_clans(expected))

    async def ensure_clan_for_context(self, context: MonsterGenerationContext, family_id: str) -> GeneratedClan:
        return await self._ensure_clan(context, family_id)

    async def _ensure_clan(
        self,
        context: MonsterGenerationContext,
        family_id: str,
    ) -> GeneratedClan:
        family = get_family_config(family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {family_id}")
        habitat_biome = context.habitat_biome
        habitat_keys = list(context.habitat_keys)
        selected_trait_keys = [
            serialize_selected_trait(trait)["key"]
            for trait in select_monster_clan_traits_for_habitat(
                family,
                biome_id=habitat_biome,
                habitat_keys=habitat_keys,
            )
        ]
        context_hash = compute_habitat_hash(biome=habitat_biome, keys=habitat_keys)
        identity_hash = compute_clan_identity_hash(
            family_id=family_id,
            biome=habitat_biome,
            keys=habitat_keys,
            selected_trait_keys=selected_trait_keys,  # type: ignore
            generation_version=2,
            resource_version=family.resource_version,
        )
        clan = await self.repository.get_clan_by_identity_hash(identity_hash)
        if clan is not None:
            return clan

        return await self.factory.build_clan_template(
            context=context,
            family_id=family_id,
            context_hash=context_hash,
            identity_hash=identity_hash,
            normalized_tags=[habitat_biome, *habitat_keys],
        )

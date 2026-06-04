from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.monsters.dto.generation import GeneratedClan, MonsterGenerationContext
    from src.backend.features.monsters.runtime.generation_builder import MonsterClanGenerationBuilder


class ClanFactory:
    """Orchestrates persisted clan templates from resource families.

    The factory owns the DB-template contract: one generated clan contains all
    variant templates available for its family/tier context. Encounter budget is
    applied later by MonsterGroupAssembler when a combat group is prepared.
    """

    def __init__(self, generator: MonsterClanGenerationBuilder) -> None:
        self.generator = generator

    async def build_clan_template(
        self,
        *,
        family_id: str,
        context: MonsterGenerationContext,
        context_hash: str,
        identity_hash: str,
        normalized_tags: Sequence[str],
        reuse_existing: bool = False,
    ) -> GeneratedClan:
        return await self.generator.generate_clan_template(
            context,
            family_id=family_id,
            context_hash=context_hash,
            identity_hash=identity_hash,
            normalized_tags=normalized_tags,
            reuse_existing=reuse_existing,
        )

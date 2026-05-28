from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.backend.core.database import get_session_context
from src.backend.features.character.runtime.combat_actor_input import CharacterCombatActorInputBuilder
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder
from src.backend.infrastructure.monsters import MonsterRepository

if TYPE_CHECKING:
    from src.backend.infrastructure.actor_commitments.manager import ActorCommitmentManager
    from src.backend.infrastructure.actor_state.managers import CharacterSessionManager


SessionContextFactory = Callable[[], AbstractAsyncContextManager[Any]]


@dataclass(frozen=True)
class CharacterCombatCommitmentResult:
    commitments: dict[str, str] = field(default_factory=dict)
    failed_players: list[int] = field(default_factory=list)
    failed_monsters: list[str] = field(default_factory=list)


class CharacterCombatCommitmentIntegration:
    """Builds temporary combat commitments from AC and monster runtime sources."""

    def __init__(
        self,
        *,
        character_sessions: CharacterSessionManager,
        commitment_manager: ActorCommitmentManager,
        session_factory: SessionContextFactory = get_session_context,
    ) -> None:
        self.character_sessions = character_sessions
        self.commitment_manager = commitment_manager
        self.session_factory = session_factory
        self.player_builder = CharacterCombatActorInputBuilder()
        self.monster_builder = MonsterCombatActorInputBuilder()

    async def prepare_commitments(
        self,
        *,
        player_ids: list[int],
        monster_ids: list[str],
        ttl: int,
    ) -> CharacterCombatCommitmentResult:
        player_snapshots, player_refs, failed_players = await self._player_commitments(player_ids)
        monster_snapshots, monster_refs, failed_monsters = await self._monster_commitments(monster_ids)
        refs_by_actor_id = {**player_refs, **monster_refs}
        saved = await self.commitment_manager.save_snapshots(
            {**player_snapshots, **monster_snapshots},
            ttl=ttl,
        )

        failed_players = [
            *failed_players,
            *[
                char_id
                for char_id in player_ids
                if char_id not in failed_players
                and not any(
                    aid in saved
                    for aid, ref in player_refs.items()
                    if ref == self.commitment_manager.source_ref("player", char_id)
                )
            ],
        ]
        failed_monsters = [
            *failed_monsters,
            *[
                monster_id
                for monster_id in monster_ids
                if monster_id not in failed_monsters
                and not any(
                    aid in saved
                    for aid, ref in monster_refs.items()
                    if ref == self.commitment_manager.source_ref("monster", monster_id)
                )
            ],
        ]

        return CharacterCombatCommitmentResult(
            commitments={
                source_ref: actor_id for actor_id, source_ref in refs_by_actor_id.items() if actor_id in saved
            },
            failed_players=failed_players,
            failed_monsters=failed_monsters,
        )

    async def _player_commitments(
        self, player_ids: list[int]
    ) -> tuple[dict[str, dict[str, Any]], dict[str, str], list[int]]:
        if not player_ids:
            return {}, {}, []

        apply_vitals_regen = getattr(self.character_sessions, "apply_vitals_regen", None)
        if apply_vitals_regen is not None:
            for char_id in player_ids:
                await apply_vitals_regen(char_id)

        sessions = await self.character_sessions.get_sessions_batch(player_ids)
        snapshots: dict[str, dict[str, Any]] = {}
        refs: dict[str, str] = {}
        failed: list[int] = []
        for char_id in player_ids:
            active_character = sessions.get(char_id)
            if not isinstance(active_character, dict):
                failed.append(char_id)
                continue
            actor_id = self.commitment_manager.actor_uuid("player", char_id)
            snapshots[actor_id] = self.player_builder.build_snapshot(active_character)
            refs[actor_id] = self.commitment_manager.source_ref("player", char_id)
        return snapshots, refs, failed

    async def _monster_commitments(
        self,
        monster_ids: list[str],
    ) -> tuple[dict[str, dict[str, Any]], dict[str, str], list[str]]:
        if not monster_ids:
            return {}, {}, []

        async with self.session_factory() as session:
            monsters = await MonsterRepository(session).get_monsters_batch(monster_ids)

        monsters_by_id = {str(monster.id): monster for monster in monsters}
        snapshots: dict[str, dict[str, Any]] = {}
        refs: dict[str, str] = {}
        failed: list[str] = []
        for monster_id in monster_ids:
            monster = monsters_by_id.get(monster_id)
            if monster is None:
                failed.append(monster_id)
                continue
            actor_id = self.commitment_manager.actor_uuid("monster", monster_id)
            snapshots[actor_id] = self.monster_builder.build_snapshot(monster)
            refs[actor_id] = self.commitment_manager.source_ref("monster", monster_id)
        return snapshots, refs, failed


__all__ = [
    "CharacterCombatCommitmentIntegration",
    "CharacterCombatCommitmentResult",
]

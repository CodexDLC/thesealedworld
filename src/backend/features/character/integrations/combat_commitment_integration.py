from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.backend.core.database import get_session_context
from src.backend.features.character.runtime.combat_actor_input import CharacterCombatActorInputBuilder
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.runtime.combat_profile import build_monster_combat_context, build_monster_vitals
from src.backend.infrastructure.monsters import MonsterRepository

if TYPE_CHECKING:
    from src.backend.features.character.managers.session import CharacterSessionManager
    from src.backend.infrastructure.actor_commitments.manager import ActorCommitmentManager


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

    async def prepare_commitments(
        self,
        *,
        scope_id: str,
        player_ids: list[int],
        monster_ids: list[str],
        ttl: int,
    ) -> CharacterCombatCommitmentResult:
        player_commitments, failed_players = await self._player_commitments(scope_id, player_ids)
        monster_commitments, failed_monsters = await self._monster_commitments(scope_id, monster_ids)
        saved = await self.commitment_manager.save_commitments(
            {**player_commitments, **monster_commitments},
            ttl=ttl,
        )

        failed_players = [
            *failed_players,
            *[
                char_id
                for char_id in player_ids
                if f"{scope_id}:player:{char_id}" not in saved and char_id not in failed_players
            ],
        ]
        failed_monsters = [
            *failed_monsters,
            *[
                monster_id
                for monster_id in monster_ids
                if f"{scope_id}:monster:{monster_id}" not in saved and monster_id not in failed_monsters
            ],
        ]

        return CharacterCombatCommitmentResult(
            commitments=saved,
            failed_players=failed_players,
            failed_monsters=failed_monsters,
        )

    async def prepare_snapshots(
        self,
        *,
        session_id: str,
        player_ids: list[int],
        monster_ids: list[str],
        ttl: int,
    ) -> CharacterCombatCommitmentResult:
        return await self.prepare_commitments(
            scope_id=session_id,
            player_ids=player_ids,
            monster_ids=monster_ids,
            ttl=ttl,
        )

    async def _player_commitments(
        self, scope_id: str, player_ids: list[int]
    ) -> tuple[dict[str, dict[str, Any]], list[int]]:
        if not player_ids:
            return {}, []

        apply_vitals_regen = getattr(self.character_sessions, "apply_vitals_regen", None)
        if apply_vitals_regen is not None:
            for char_id in player_ids:
                await apply_vitals_regen(char_id)

        sessions = await self.character_sessions.get_sessions_batch(player_ids)
        async with self.session_factory() as session:
            equipped_by_char = await ItemInstanceRepository(session).get_equipped_for_characters(player_ids)

        snapshots: dict[str, dict[str, Any]] = {}
        failed: list[int] = []
        for char_id in player_ids:
            active_character = sessions.get(char_id)
            if not isinstance(active_character, dict):
                failed.append(char_id)
                continue
            active_character = self._with_equipped_items(active_character, equipped_by_char.get(char_id, []))
            snapshots[f"{scope_id}:player:{char_id}"] = self.player_builder.build_snapshot(active_character)
        return snapshots, failed

    @staticmethod
    def _with_equipped_items(active_character: dict[str, Any], equipped_items: list[dict[str, Any]]) -> dict[str, Any]:
        if not equipped_items:
            return active_character

        items = dict(active_character.get("items") or {})
        layout = dict(items.get("layout") or {})
        equipment = dict(layout.get("equipment") or {})
        by_id = dict(items.get("by_id") or {})

        for item in equipped_items:
            item_id = str(item.get("item_id") or "")
            slot = str(item.get("slot") or "")
            if not item_id:
                continue
            by_id[item_id] = item
            if not slot:
                continue
            equipment[slot] = item_id
            if slot == "two_hand":
                equipment["off_hand"] = None
            elif slot in {"main_hand", "off_hand"} and equipment.get("two_hand"):
                equipment["two_hand"] = None

        return {
            **active_character,
            "items": {
                **items,
                "layout": {**layout, "equipment": equipment},
                "by_id": by_id,
            },
        }

    async def _monster_commitments(
        self,
        scope_id: str,
        monster_ids: list[str],
    ) -> tuple[dict[str, dict[str, Any]], list[str]]:
        if not monster_ids:
            return {}, []

        async with self.session_factory() as session:
            monsters = await MonsterRepository(session).get_monsters_batch(monster_ids)

        monsters_by_id = {str(monster.id): monster for monster in monsters}
        snapshots: dict[str, dict[str, Any]] = {}
        failed: list[str] = []
        for monster_id in monster_ids:
            monster = monsters_by_id.get(str(monster_id))
            if monster is None:
                failed.append(str(monster_id))
                continue
            vitals = build_monster_vitals(monster)
            _family = get_family_config(monster.family_id) if monster.family_id else None
            _archetype = _family.archetype if _family else "humanoid"
            snapshots[f"{scope_id}:monster:{monster_id}"] = {
                "meta": {
                    "actor_type": "monster",
                    "actor_id": str(monster.id),
                    "name": monster.name_ru,
                    "role": monster.role,
                    "tags": ["monster", monster.role],
                    "archetype": _archetype,
                },
                "runtime": {"vitals": vitals},
                "combat": build_monster_combat_context(monster),
                "status": vitals,
                "source": {
                    "monster_id": str(monster.id),
                    "template_id": monster.variant_key,
                    "clan_id": str(monster.clan_id),
                    "db_refs": {"generated_monsters": str(monster.id), "generated_clans": str(monster.clan_id)},
                },
            }
        return snapshots, failed


__all__ = [
    "CharacterCombatCommitmentIntegration",
    "CharacterCombatCommitmentResult",
]

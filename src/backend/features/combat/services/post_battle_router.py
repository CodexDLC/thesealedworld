from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.loot.integrations.loot_integration import LootIntegration
from src.backend.infrastructure.loot.managers.loot_manager import LootManager
from src.shared.enums import CoreDomain
from src.shared.schemas.combat import (
    PostCombatLootCorpseDTO,
    PostCombatLootItemDTO,
    PostCombatOutcomeDTO,
)

if TYPE_CHECKING:
    from src.shared.schemas.loot import CorpseDTO


class CombatPostBattleRouter:
    """Builds per-player post-combat routing decisions from a finalized battle."""

    async def build_outcomes(
        self, ctx: dict[str, Any], finalization: dict[str, Any]
    ) -> dict[int, PostCombatOutcomeDTO]:
        combat_id = str(finalization.get("combat_id") or "")
        actors = finalization.get("actors") if isinstance(finalization.get("actors"), dict) else {}
        meta = finalization.get("meta") if isinstance(finalization.get("meta"), dict) else {}
        battle_type = str(meta.get("battle_type") or "").lower()
        location_id = str(meta.get("location_id") or "")
        arena_session_id = str(meta.get("arena_session_id") or "")
        winner_team = str(finalization.get("winner_team") or "")
        participant_char_ids = [
            int(char_id) for char_id in finalization.get("participant_char_ids", []) if _int_or_none(char_id)
        ]
        dead_char_ids = {
            int(actor.get("char_id"))
            for actor in actors.values()
            if isinstance(actor, dict) and actor.get("char_id") is not None and actor.get("is_dead") is True
        }
        winner_char_ids = [
            int(actor.get("char_id"))
            for actor in actors.values()
            if isinstance(actor, dict)
            and actor.get("char_id") is not None
            and str(actor.get("team") or "") == winner_team
            and actor.get("is_dead") is not True
        ]

        is_arena = bool(arena_session_id) or battle_type in {"arena", "pvp", "pvp_arena", "shadow"}
        if is_arena:
            return {
                char_id: self._arena_outcome(
                    char_id,
                    combat_id=combat_id,
                    battle_type=battle_type,
                    shadow=battle_type == "shadow",
                )
                for char_id in participant_char_ids
            }

        pending_corpses_by_actor = await self._pending_corpses_by_actor(ctx, combat_id)
        dead_monster_corpse_ids = self._dead_monster_corpse_ids(actors, pending_corpses_by_actor)
        loot_corpses = await self._activate_and_load_loot(
            ctx,
            corpse_ids=dead_monster_corpse_ids,
            char_ids=winner_char_ids,
            location_id=location_id,
        )

        outcomes: dict[int, PostCombatOutcomeDTO] = {}
        for char_id in participant_char_ids:
            if char_id in dead_char_ids:
                outcomes[char_id] = await self._death_outcome(ctx, char_id, combat_id=combat_id)
                continue
            if char_id in winner_char_ids and loot_corpses:
                outcomes[char_id] = self._loot_outcome(
                    char_id,
                    combat_id=combat_id,
                    location_id=location_id,
                    corpses=loot_corpses,
                )
                continue
            outcomes[char_id] = PostCombatOutcomeDTO(
                char_id=char_id,
                combat_id=combat_id,
                outcome="return",
                target_state=CoreDomain.EXPLORATION.value,
                notice="Бой завершен. Можно осмотреться вокруг.",
            )
        return outcomes

    @staticmethod
    def _arena_outcome(
        char_id: int,
        *,
        combat_id: str,
        battle_type: str,
        shadow: bool,
    ) -> PostCombatOutcomeDTO:
        return PostCombatOutcomeDTO(
            char_id=char_id,
            combat_id=combat_id,
            outcome="arena_shadow" if shadow else "arena",
            target_state=CoreDomain.ARENA.value,
            notice="Тренировочный бой завершен. Рейтинг не изменился."
            if shadow
            else "Бой арены завершен. Изменение рейтинга будет показано в арене.",
            rating_delta=None,
            loot_context={"battle_type": battle_type},
        )

    async def _death_outcome(self, ctx: dict[str, Any], char_id: int, *, combat_id: str) -> PostCombatOutcomeDTO:
        session_doc = await self._active_session(ctx, char_id)
        sessions = session_doc.get("sessions") if isinstance(session_doc, dict) else {}
        risk = session_doc.get("risk") if isinstance(session_doc, dict) else {}
        pending = session_doc.get("pending_progress") if isinstance(session_doc, dict) else {}
        death_summary = {
            "run_id": sessions.get("death_run_id") if isinstance(sessions, dict) else None,
            "corpse_id": sessions.get("death_corpse_id") if isinstance(sessions, dict) else None,
            "pending_free_xp": _float_value((pending or {}).get("free_xp")),
            "pending_skill_count": len((pending or {}).get("skills") or {}),
            "carried_item_count": int((risk or {}).get("carried_item_count") or 0),
            "carried_resource_count": int((risk or {}).get("carried_resource_count") or 0),
            "dropped_items": await self._corpse_items(
                ctx, sessions.get("death_corpse_id") if isinstance(sessions, dict) else None
            ),
        }
        return PostCombatOutcomeDTO(
            char_id=char_id,
            combat_id=combat_id,
            outcome="death",
            target_state=CoreDomain.DEATH.value,
            notice="Поход оборвался. Накопленный вне города прогресс будет потерян при возврате.",
            death_summary=death_summary,
        )

    async def _corpse_items(self, ctx: dict[str, Any], corpse_id: Any) -> list[dict[str, Any]]:
        redis_service = ctx.get("redis_service")
        if redis_service is None or not corpse_id:
            return []
        corpse = await LootIntegration(LootManager(redis_service)).get_corpse(str(corpse_id))
        if corpse is None:
            return []
        return [
            {
                "item_id": item.id,
                "template_id": item.template_id,
                "name": item.name,
                "rarity": item.rarity,
                "amount": item.amount,
                "instance_id": item.instance_id,
                "is_resource": item.is_resource,
            }
            for item in corpse.items
        ]

    @staticmethod
    def _loot_outcome(
        char_id: int,
        *,
        combat_id: str,
        location_id: str,
        corpses: list[CorpseDTO],
    ) -> PostCombatOutcomeDTO:
        corpse_rows = [
            PostCombatLootCorpseDTO(
                corpse_id=corpse.id,
                name=corpse.monster_name,
                corpse_type=corpse.corpse_type,
                items=[
                    PostCombatLootItemDTO(
                        item_id=item.id,
                        template_id=item.template_id,
                        name=item.name,
                        rarity=item.rarity,
                        amount=item.amount,
                        source=corpse.monster_name,
                        instance_id=item.instance_id,
                        is_resource=item.is_resource,
                    )
                    for item in corpse.items
                ],
            ).model_dump(mode="json")
            for corpse in corpses
        ]
        corpse_ids = [corpse.id for corpse in corpses]
        return PostCombatOutcomeDTO(
            char_id=char_id,
            combat_id=combat_id,
            outcome="loot_available",
            target_state=CoreDomain.LOOT.value,
            notice="После боя остался лут.",
            corpse_ids=corpse_ids,
            loot_context={
                "location_id": location_id,
                "corpse_ids": corpse_ids,
                "corpses": corpse_rows,
            },
        )

    @staticmethod
    def _dead_monster_corpse_ids(
        actors: dict[str, Any],
        pending_corpses_by_actor: dict[str, str],
    ) -> list[str]:
        corpse_ids: list[str] = []
        for actor_id, actor in actors.items():
            if not isinstance(actor, dict) or actor.get("is_dead") is not True:
                continue
            if actor.get("char_id") is not None:
                continue
            corpse_id = pending_corpses_by_actor.get(str(actor_id))
            if corpse_id:
                corpse_ids.append(corpse_id)
        return corpse_ids

    async def _pending_corpses_by_actor(self, ctx: dict[str, Any], combat_id: str) -> dict[str, str]:
        redis_service = ctx.get("redis_service")
        if redis_service is None or not combat_id:
            return {}
        client = redis_service.redis_client if hasattr(redis_service, "redis_client") else redis_service.pipeline.client
        raw = await client.get(f"loot:pending:{combat_id}")
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("CombatPostBattleRouter | invalid pending loot json combat_id={}", combat_id)
            return {}
        if not isinstance(value, dict):
            logger.warning("CombatPostBattleRouter | pending loot is not actor map combat_id={}", combat_id)
            return {}
        return {str(actor_id): str(corpse_id) for actor_id, corpse_id in value.items() if corpse_id}

    async def _activate_and_load_loot(
        self,
        ctx: dict[str, Any],
        *,
        corpse_ids: list[str],
        char_ids: list[int],
        location_id: str,
    ) -> list[CorpseDTO]:
        redis_service = ctx.get("redis_service")
        if redis_service is None or not corpse_ids:
            return []
        manager = LootManager(redis_service)
        integration = LootIntegration(manager)
        if location_id:
            await integration.activate_corpses(corpse_ids, char_ids, location_id)
        corpses: list[CorpseDTO] = []
        for corpse_id in corpse_ids:
            corpse = await integration.get_corpse(corpse_id)
            if corpse is not None and corpse.items:
                corpses.append(corpse)
        return corpses

    @staticmethod
    async def _active_session(ctx: dict[str, Any], char_id: int) -> dict[str, Any]:
        character_sessions = ctx.get("character_sessions")
        if character_sessions is None:
            return {}
        value = await character_sessions.get_session(char_id)
        return value if isinstance(value, dict) else {}


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_value(value: Any) -> float:
    try:
        return round(float(value or 0.0), 4)
    except (TypeError, ValueError):
        return 0.0

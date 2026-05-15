from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.backend.features.combat.dto.action import CombatActionDTO
    from src.backend.features.combat.dto.actor import ActorSnapshot
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO
    from src.backend.features.combat.dto.session import BattleContext


class CombatLogActorContextDTO(BaseModel):
    id: str
    name: str
    team: str | None = None
    actor_type: str | None = None
    taxonomy: str = "humanoid"
    hp: int | None = None
    max_hp: int | None = None
    en: int | None = None
    max_en: int | None = None
    stats: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_actor(cls, actor: ActorSnapshot) -> CombatLogActorContextDTO:
        stats: dict[str, Any] = {}
        if actor.stats is not None:
            stats = {
                "mods": actor.stats.mods.model_dump(mode="json"),
                "skills": actor.stats.skills.model_dump(mode="json"),
            }
        return cls(
            id=str(actor.char_id),
            name=actor.meta.name or f"#{actor.char_id}",
            team=actor.meta.team,
            actor_type=actor.meta.type,
            taxonomy=actor.meta.archetype or "humanoid",
            hp=actor.meta.hp,
            max_hp=actor.meta.max_hp,
            en=actor.meta.en,
            max_en=actor.meta.max_en,
            stats=stats,
        )


class CombatResultSupportTaskDTO(BaseModel):
    session_id: str
    global_turn: int
    wave: int
    seq: int
    timestamp: float
    result: dict[str, Any]
    action: dict[str, Any]
    actors: dict[str, CombatLogActorContextDTO] = Field(default_factory=dict)
    stat_slice: dict[str, dict[str, float | str]] = Field(default_factory=dict)

    @classmethod
    def from_context(
        cls,
        *,
        ctx: BattleContext,
        result: InteractionResultDTO,
        action: CombatActionDTO,
        wave: int,
        seq: int,
        timestamp: float,
    ) -> CombatResultSupportTaskDTO:
        actors = cls._actors_for_result(ctx, result)
        return cls(
            session_id=ctx.session_id,
            global_turn=ctx.meta.step_counter + 1,
            wave=wave,
            seq=seq,
            timestamp=timestamp,
            result=result.model_dump(mode="json"),
            action=action.model_dump(mode="json"),
            actors=actors,
            stat_slice=cls._stat_slice(actors, result),
        )

    @staticmethod
    def _actors_for_result(
        ctx: BattleContext,
        result: InteractionResultDTO,
    ) -> dict[str, CombatLogActorContextDTO]:
        actor_ids = [result.source_id, result.target_id]
        actors: dict[str, CombatLogActorContextDTO] = {}
        for actor_id in actor_ids:
            if actor_id is None:
                continue
            actor = ctx.get_actor(actor_id)
            if actor is not None:
                actors[str(actor_id)] = CombatLogActorContextDTO.from_actor(actor)
        return actors

    @staticmethod
    def _stat_slice(
        actors: dict[str, CombatLogActorContextDTO],
        result: InteractionResultDTO,
    ) -> dict[str, dict[str, float | str]]:
        return {
            "s": CombatResultSupportTaskDTO._actor_stats(actors.get(str(result.source_id))),
            "d": CombatResultSupportTaskDTO._actor_stats(actors.get(str(result.target_id))),
        }

    @staticmethod
    def _actor_stats(actor: CombatLogActorContextDTO | None) -> dict[str, float | str]:
        if actor is None:
            return {}
        mods = actor.stats.get("mods")
        skills = actor.stats.get("skills")
        if not isinstance(mods, dict) or not isinstance(skills, dict):
            return {}
        return {
            "acc": float(mods.get("accuracy", 0.0)),
            "crit": float(mods.get("crit_chance", 0.0)),
            "eva": float(mods.get("evasion", 0.0)),
            "par": float(mods.get("parry", 0.0)),
            "blk": float(mods.get("block", 0.0)),
            "arm": float(mods.get("armor", 0.0)),
            "sup": float(mods.get("physical_suppression", 0.0)),
            "ap": float(mods.get("armor_penetration_pct", 0.0)),
            "sp": float(skills.get("skill_parrying", 0.0)),
        }

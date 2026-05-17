from __future__ import annotations

import contextlib
import json
import time
from typing import TYPE_CHECKING, Any

from src.backend.features.combat.runtime.support.analytics_builder import ANALYTICS_SCHEMA_VERSION, COMBAT_MATH_VERSION

if TYPE_CHECKING:
    from src.backend.features.combat.runtime.services.experience_finalizer import CombatActorExperienceResult


class CombatFinalizationBuilder:
    """Builds an immutable combat result snapshot from the live runtime session."""

    async def build(
        self,
        data_service: Any,
        session_id: str,
        winner: str,
        *,
        progression_results: dict[str, CombatActorExperienceResult] | None = None,
    ) -> dict[str, Any]:
        meta = await data_service.get_meta(session_id)
        meta = meta if isinstance(meta, dict) else {}
        actor_ids = [str(actor_id) for actor_id in data_service.actor_ids_from_meta(meta)]
        actors = await data_service.get_actors_batch(session_id, actor_ids)
        analytics = await self._get_analytics(data_service, session_id)
        logs_by_turn = await self._get_logs_by_turn(data_service, session_id)
        teams = self._decode_json(meta.get("teams"), default={})
        dead_actors = {str(actor_id) for actor_id in self._decode_json(meta.get("dead_actors"), default=[])}

        actor_payloads = self._actors_payload(
            actors,
            dead_actor_ids=dead_actors,
            progression_results=progression_results or {},
        )
        participant_char_ids = [
            int(actor_id)
            for actor_id, actor in actor_payloads.items()
            if actor.get("char_id") is not None and str(actor_id).isdigit()
        ]
        report = self._report(
            winner=winner,
            teams=teams,
            actors=actor_payloads,
            logs_by_turn=logs_by_turn,
        )

        return {
            "schema_version": 2,
            "combat_id": session_id,
            "status": "finalized",
            "winner_team": winner,
            "finished_at": int(time.time()),
            "participant_char_ids": participant_char_ids,
            "meta": {
                "source": self._optional_str(meta.get("source")),
                "battle_type": self._optional_str(meta.get("battle_type")),
                "location_id": self._optional_str(meta.get("location_id")),
                "arena_session_id": self._optional_str(meta.get("arena_session_id")),
                "started_at": self._optional_int(meta.get("start_time")),
            },
            "teams": teams if isinstance(teams, dict) else {},
            "actors": actor_payloads,
            "report": report,
            "analytics": self._normalize_analytics(analytics),
            "reward_hooks": [],
        }

    @classmethod
    def _actors_payload(
        cls,
        actors: dict[str, Any],
        *,
        dead_actor_ids: set[str],
        progression_results: dict[str, CombatActorExperienceResult],
    ) -> dict[str, dict[str, Any]]:
        payload: dict[str, dict[str, Any]] = {}
        for actor_id, actor in actors.items():
            if not isinstance(actor, dict):
                continue
            actor_id = str(actor_id)
            raw_meta = actor.get("meta")
            meta: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}
            xp_buffer = cls._float_mapping(actor.get("xp_buffer"))
            progression = progression_results.get(actor_id)
            progression_payload = progression.rewards if progression is not None else {}
            hp = cls._optional_int(meta.get("hp")) or 0
            payload[actor_id] = {
                "actor_id": actor_id,
                "char_id": int(actor_id) if actor_id.isdigit() else None,
                "name": str(meta.get("name") or actor_id),
                "team": cls._optional_str(meta.get("team")) or "neutral",
                "actor_type": cls._optional_str(meta.get("type")) or "unknown",
                "is_ai": bool(meta.get("is_ai", False)),
                "is_dead": actor_id in dead_actor_ids or bool(meta.get("is_dead", False)) or hp <= 0,
                "vitals_final": {
                    "hp": hp,
                    "max_hp": cls._optional_int(meta.get("max_hp")) or 1,
                    "en": cls._optional_int(meta.get("en")) or 0,
                    "max_en": cls._optional_int(meta.get("max_en")) or 1,
                    "stamina": cls._optional_int(meta.get("stamina")) or 0,
                    "max_stamina": cls._optional_int(meta.get("max_stamina")) or 1,
                },
                "xp_buffer": xp_buffer,
                "progression": progression_payload,
                "used_skill_keys": sorted(key for key in progression_payload if key.startswith("skill_")),
            }
        return payload

    @classmethod
    def _report(
        cls,
        *,
        winner: str,
        teams: Any,
        actors: dict[str, dict[str, Any]],
        logs_by_turn: dict[str, list[str]],
    ) -> dict[str, Any]:
        team_map = teams if isinstance(teams, dict) else {}
        team_reports = []
        for team, members in team_map.items():
            member_ids = [str(member) for member in members] if isinstance(members, list) else []
            actor_rows = [actors[actor_id] for actor_id in member_ids if actor_id in actors]
            team_reports.append(
                {
                    "team": str(team),
                    "outcome": cls._team_outcome(str(team), winner),
                    "actors": [
                        {
                            "actor_id": actor["actor_id"],
                            "name": actor["name"],
                            "actor_type": actor["actor_type"],
                            "is_dead": actor["is_dead"],
                        }
                        for actor in actor_rows
                    ],
                }
            )
        last_turn = cls._last_log_turn(logs_by_turn)
        return {
            "winner_team": winner,
            "turns": len(logs_by_turn),
            "last_turn": last_turn,
            "teams": team_reports,
        }

    @staticmethod
    def _team_outcome(team: str, winner: str) -> str:
        if winner == "draw":
            return "draw"
        return "victory" if team == winner else "defeat"

    @staticmethod
    async def _get_analytics(data_service: Any, session_id: str) -> dict[str, Any]:
        getter = getattr(data_service, "get_analytics", None)
        if getter is None:
            return {}
        value = await getter(session_id)
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _normalize_analytics(analytics: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(analytics)
        normalized.setdefault("analytics_schema_version", ANALYTICS_SCHEMA_VERSION)
        normalized.setdefault("combat_math_version", COMBAT_MATH_VERSION)
        return normalized

    @staticmethod
    async def _get_logs_by_turn(data_service: Any, session_id: str) -> dict[str, list[str]]:
        getter = getattr(data_service, "get_logs_by_turn", None)
        if getter is None:
            return {}
        value = await getter(session_id)
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _decode_json(value: Any, *, default: Any) -> Any:
        if isinstance(value, dict | list):
            return value
        if value in (None, ""):
            return default
        with contextlib.suppress(json.JSONDecodeError):
            return json.loads(str(value))
        return default

    @staticmethod
    def _last_log_turn(logs_by_turn: dict[str, list[str]]) -> int | None:
        numeric_turns: list[int] = []
        for turn in logs_by_turn:
            with contextlib.suppress(TypeError, ValueError):
                numeric_turns.append(int(turn))
        return max(numeric_turns) if numeric_turns else None

    @staticmethod
    def _float_mapping(value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            return {}
        result: dict[str, float] = {}
        for key, raw in value.items():
            with contextlib.suppress(TypeError, ValueError):
                result[str(key)] = float(raw or 0.0)
        return result

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        with contextlib.suppress(TypeError, ValueError):
            return int(value)
        return None

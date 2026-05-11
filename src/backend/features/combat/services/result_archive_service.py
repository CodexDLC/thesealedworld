from __future__ import annotations

import contextlib
from typing import Any

from src.backend.core.database import get_session_context
from src.backend.infrastructure.combat.repositories import CombatFinalizationRepository
from src.shared.schemas.combat import CombatResultActionDTO, CombatResultDTO


class CombatResultArchiveService:
    """Reads finished combat results from the archive boundary.

    TODO(combat-archive): Replace this stub with a real archive repository once
    combat finalization persists immutable session results outside Redis runtime
    keys.
    """

    async def load_finalization_for_character(
        self,
        data_service: Any,
        char_id: int,
        *,
        combat_id: str | None = None,
        finalization_id: str | None = None,
    ) -> dict[str, Any] | None:
        finalization = await self._load_from_redis(
            data_service,
            char_id,
            combat_id=combat_id,
            finalization_id=finalization_id,
        )
        if finalization is not None:
            return finalization
        if not hasattr(data_service, "get_finalization"):
            return None
        with contextlib.suppress(Exception):
            return await self._load_from_db(char_id, combat_id=finalization_id or combat_id)
        return None

    def build_result_from_finalization(
        self,
        finalization: dict[str, Any],
        *,
        char_id: int,
        reason: str,
        target_state: str,
    ) -> CombatResultDTO:
        combat_id = self._optional_str(finalization.get("combat_id"))
        winner = self._optional_str(finalization.get("winner_team"))
        actors = finalization.get("actors") if isinstance(finalization.get("actors"), dict) else {}
        teams = {
            str(team): [str(member) for member in members]
            for team, members in (
                finalization.get("teams") if isinstance(finalization.get("teams"), dict) else {}
            ).items()
            if isinstance(members, list)
        }
        report = self._complete_report(
            finalization.get("report") if isinstance(finalization.get("report"), dict) else {},
            teams=teams,
            actors=actors,
            winner=winner,
        )
        outcome = self._outcome_for_actor(finalization, char_id=char_id)
        return CombatResultDTO(
            combat_id=combat_id,
            char_id=char_id,
            status="finished",
            outcome=outcome,
            title=self._result_title(outcome),
            message="Бой завершен. Итог сохранен в финальном отчете.",
            summary=self._summary(outcome=outcome, winner=winner, report=report),
            reason=reason,
            archived=True,
            teams=teams,
            actors=actors,
            report=report,
            rewards=self._actor_progression(actors, char_id),
            reward_hooks=[dict(item) for item in finalization.get("reward_hooks", []) if isinstance(item, dict)],
            metadata={
                "source": "combat_finalization",
                "winner": winner,
                "viewer_team": self._viewer_team(finalization, char_id),
                "battle_type": (finalization.get("meta") or {}).get("battle_type")
                if isinstance(finalization.get("meta"), dict)
                else None,
            },
            primary_action=CombatResultActionDTO(
                label="Продолжить",
                action="navigate",
                target_state=target_state,
            ),
        )

    async def get_result_for_character(
        self,
        char_id: int,
        *,
        combat_id: str | None = None,
        reason: str = "combat_session_not_found",
        target_state: str = "exploration",
    ) -> CombatResultDTO:
        return CombatResultDTO(
            combat_id=combat_id,
            char_id=char_id,
            title="Итоги боя недоступны",
            message="Живая боевая сессия больше не найдена.",
            summary=(
                "Результат боя будет загружаться из архивного хранилища после внедрения финализации. "
                "Сейчас сохраненного архива для этой сессии нет."
            ),
            reason=reason,
            metadata={"source": "combat_archive_stub"},
            primary_action=CombatResultActionDTO(
                label="Продолжить",
                action="navigate",
                target_state=target_state,
            ),
        )

    async def _load_from_redis(
        self,
        data_service: Any,
        char_id: int,
        *,
        combat_id: str | None,
        finalization_id: str | None = None,
    ) -> dict[str, Any] | None:
        get_finalization = getattr(data_service, "get_finalization", None)
        if get_finalization is None:
            return None

        candidate_id = finalization_id or combat_id
        if not candidate_id:
            get_latest = getattr(data_service, "get_latest_finalization_id_for_character", None)
            candidate_id = await get_latest(char_id) if get_latest is not None else None
        if not candidate_id:
            return None

        value = await get_finalization(candidate_id)
        return value if isinstance(value, dict) else None

    async def _load_from_db(self, char_id: int, *, combat_id: str | None) -> dict[str, Any] | None:
        async with get_session_context() as session:
            repo = CombatFinalizationRepository(session)
            row = await repo.get_by_combat_id(combat_id) if combat_id else await repo.get_latest_for_character(char_id)
            if row is None:
                return None
            return dict(row.finalization or {})

    @staticmethod
    def _outcome_for_actor(finalization: dict[str, Any], *, char_id: int) -> str:
        winner = CombatResultArchiveService._optional_str(finalization.get("winner_team"))
        if not winner:
            return "unknown"
        if winner == "draw":
            return "draw"
        viewer_team = CombatResultArchiveService._viewer_team(finalization, char_id)
        if not viewer_team:
            return "unknown"
        return "victory" if viewer_team == winner else "defeat"

    @staticmethod
    def _viewer_team(finalization: dict[str, Any], char_id: int) -> str | None:
        teams = finalization.get("teams")
        if not isinstance(teams, dict):
            return None
        actor_id = str(char_id)
        for team, members in teams.items():
            if isinstance(members, list) and actor_id in {str(member) for member in members}:
                return str(team)
        return None

    @staticmethod
    def _result_title(outcome: str) -> str:
        return {"victory": "Победа", "defeat": "Поражение", "draw": "Ничья"}.get(outcome, "Итоги боя")

    @staticmethod
    def _summary(*, outcome: str, winner: str | None, report: dict[str, Any]) -> str:
        leads = {
            "victory": "Ваша команда победила.",
            "defeat": "Ваша команда проиграла.",
            "draw": "Бой завершился ничьей.",
        }
        parts = [leads.get(outcome, "Бой завершен, но итог для персонажа не удалось определить.")]
        if winner and outcome == "unknown":
            parts.append(f"Победитель: {winner}.")
        last_turn = report.get("last_turn")
        if last_turn is not None:
            parts.append(f"Последний ход в журнале: {last_turn}.")
        return " ".join(parts)

    @staticmethod
    def _complete_report(
        report: dict[str, Any],
        *,
        teams: dict[str, list[str]],
        actors: dict[str, Any],
        winner: str | None,
    ) -> dict[str, Any]:
        result = dict(report)
        if isinstance(result.get("teams"), list) and result["teams"]:
            return result
        team_reports = []
        for team, member_ids in teams.items():
            team_reports.append(
                {
                    "team": team,
                    "outcome": CombatResultArchiveService._team_outcome(team, winner),
                    "actors": [
                        {
                            "actor_id": actor_id,
                            "name": actor.get("name", actor_id) if isinstance(actor, dict) else actor_id,
                            "actor_type": actor.get("actor_type", "unknown") if isinstance(actor, dict) else "unknown",
                            "is_dead": bool(actor.get("is_dead", False)) if isinstance(actor, dict) else False,
                        }
                        for actor_id in member_ids
                        for actor in [actors.get(actor_id)]
                    ],
                }
            )
        result["teams"] = team_reports
        return result

    @staticmethod
    def _team_outcome(team: str, winner: str | None) -> str:
        if winner == "draw":
            return "draw"
        if winner:
            return "victory" if team == winner else "defeat"
        return "unknown"

    @staticmethod
    def _actor_progression(actors: dict[str, Any], char_id: int) -> dict[str, Any]:
        actor = actors.get(str(char_id))
        if not isinstance(actor, dict):
            return {}
        progression = actor.get("progression")
        return {"progression": progression} if isinstance(progression, dict) else {}

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

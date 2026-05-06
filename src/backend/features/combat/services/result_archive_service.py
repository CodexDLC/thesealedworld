from __future__ import annotations

from src.shared.schemas.combat import CombatResultActionDTO, CombatResultDTO


class CombatResultArchiveService:
    """Reads finished combat results from the archive boundary.

    TODO(combat-archive): Replace this stub with a real archive repository once
    combat finalization persists immutable session results outside Redis runtime
    keys.
    """

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

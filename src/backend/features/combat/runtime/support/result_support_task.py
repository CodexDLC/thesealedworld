from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.features.combat.runtime.support.analytics_builder import CombatAnalyticsFactBuilder

if TYPE_CHECKING:
    from src.backend.features.combat.runtime.support.dto import CombatResultSupportTaskDTO


class CombatResultSupportTask:
    """Post-result support work for machine-readable combat analytics."""

    async def process(self, *, data_service: Any, payload: CombatResultSupportTaskDTO) -> None:
        analytics_fact = CombatAnalyticsFactBuilder.build_result_fact_from_support_payload(payload)

        await self._store_analytics(data_service, payload.session_id, analytics_fact)

    async def _store_analytics(self, data_service: Any, session_id: str, fact: dict[str, Any]) -> None:
        append = getattr(data_service, "append_analytics", None)
        if append is not None:
            await append(session_id, fact)
            return

        log.warning("CombatResultSupport | skip=analytics reason=no_append_method session_id={}", session_id)

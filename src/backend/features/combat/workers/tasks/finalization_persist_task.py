from __future__ import annotations

from loguru import logger as log

from src.backend.core.database import get_session_context
from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001
from src.backend.infrastructure.combat.repositories import CombatFinalizationRepository


async def combat_finalization_persist_task(ctx: dict, payload: dict) -> None:
    combat_id = str(payload.get("combat_id") or "")
    if not combat_id:
        log.warning("CombatFinalizationPersist | reason=missing_combat_id")
        return

    data_service: CombatDataService | None = ctx.get("combat_data_service")
    if data_service is None:
        log.error("CombatFinalizationPersist | reason=no_data_service combat_id={}", combat_id)
        return

    get_finalization = getattr(data_service, "get_finalization", None)
    finalization = await get_finalization(combat_id) if get_finalization is not None else None
    if not isinstance(finalization, dict):
        log.warning("CombatFinalizationPersist | reason=missing_cache combat_id={}", combat_id)
        return

    async with get_session_context() as session:
        await CombatFinalizationRepository(session).upsert_from_payload(finalization)

    log.info("CombatFinalizationPersist | status=success combat_id={}", combat_id)

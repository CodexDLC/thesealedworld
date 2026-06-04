from __future__ import annotations

from loguru import logger as log

from src.backend.core.database import get_session_context
from src.backend.core.mongo import get_mongo_provider
from src.backend.features.combat.runtime.analytics import CombatAnalyticsIngestionService
from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001
from src.backend.infrastructure.combat.repositories import CombatFinalizationRepository
from src.backend.infrastructure.mongo import CombatDocumentRepository
from src.shared.infrastructure.log_task_wrapper import logged_task


@logged_task
async def combat_finalization_persist_task(ctx: dict, payload: dict) -> None:
    """Persist frozen combat finalization data into durable storage."""
    combat_id = str(payload.get("combat_id") or "")
    if not combat_id:
        log.bind(reason="missing_combat_id").warning("CombatFinalizationPersistSkipped")
        return

    data_service: CombatDataService | None = ctx.get("combat_data_service")
    if data_service is None:
        log.bind(reason="no_data_service", combat_id=combat_id).error("CombatFinalizationPersistFailed")
        return

    get_finalization = getattr(data_service, "get_finalization", None)
    finalization = await get_finalization(combat_id) if get_finalization is not None else None
    if not isinstance(finalization, dict):
        log.bind(reason="missing_cache", combat_id=combat_id).warning("CombatFinalizationPersistSkipped")
        return

    exchanges = CombatAnalyticsIngestionService.extract_exchange_facts(finalization, include_trace=True)
    combat_document = CombatAnalyticsIngestionService.build_combat_document(finalization, exchanges)
    mongo_row = await CombatDocumentRepository(get_mongo_provider().database()).upsert(combat_document)  # type: ignore
    mongo_document_id = str(mongo_row.get("_id") or "")

    async with get_session_context() as session:
        await CombatFinalizationRepository(session).upsert_from_payload(
            finalization,
            mongo_document_id=mongo_document_id,
            mongo_status="stored",
        )
        await CombatAnalyticsIngestionService.ingest_finalization(
            session,
            finalization,
            aggregate_version=1,
            mongo_document_id=mongo_document_id,
        )

    log.bind(combat_id=combat_id, status="success").info("CombatFinalizationPersistCompleted")

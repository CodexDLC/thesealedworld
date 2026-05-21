from loguru import logger as log

from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001
from src.backend.features.combat.runtime.support import CombatResultSupportTask, CombatResultSupportTaskDTO
from src.shared.infrastructure.log_task_wrapper import logged_task


@logged_task
async def combat_result_support_task(ctx: dict, payload: dict) -> None:
    """Process deferred support work emitted by the combat executor."""
    session_id = str(payload.get("session_id", "unknown"))
    data_service: CombatDataService | None = ctx.get("combat_data_service")
    if data_service is None:
        log.bind(reason="no_data_service", session_id=session_id).error("CombatResultSupportFailed")
        return

    dto = CombatResultSupportTaskDTO.model_validate(payload)
    await CombatResultSupportTask().process(data_service=data_service, payload=dto)

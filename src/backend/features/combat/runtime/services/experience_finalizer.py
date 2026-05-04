from loguru import logger as log

from src.backend.features.combat.runtime.services.data_service import CombatDataService


class CombatExperienceFinalizer:
    """
    Boundary for end-of-combat XP projection.

    Runtime mechanics already fills actor xp_buffer during exchanges. The final XP model
    is intentionally deferred until the reward contract is designed.
    """

    async def finalize(self, data_service: CombatDataService, session_id: str, winner: str) -> None:
        """
        No-op placeholder called from victory finalization.

        TODO(combat-xp): Design final XP contract:
        - load actors, skills, weapon/loadout, and accumulated xp_buffer/action counters;
        - map technical action keys into skill-specific XP rewards;
        - persist awarded XP through the player progression boundary;
        - clear or archive xp_buffer together with final combat history.
        """
        log.debug(
            "CombatXPFinalizer | status=deferred session_id={session_id} winner={winner}",
            session_id=session_id,
            winner=winner,
        )

from typing import Any

from aiogram.fsm.context import FSMContext
from codex_bot.fsm.state_manager import BaseStateManager


class CommunityFeedStateManager(BaseStateManager):
    """
    Isolated FSM State Manager for the CommunityFeed feature.
    All data is stored under the 'draft:community_feed' key.

    Add your typed methods here for cleaner business logic.
    """

    def __init__(self, state: FSMContext):
        super().__init__(state, feature_key="community_feed")

    async def get_current_data(self) -> dict[str, Any]:
        """Returns all data of the current feature draft."""
        return await self.get_payload()

    # --- Examples of custom typed methods ---
    # async def save_step(self, step_name: str):
    #     await self.update(step=step_name)
    #
    # async def get_step(self) -> Optional[str]:
    #     return await self.get_value("step")

from __future__ import annotations

from typing import Any

from codex_bot.base import UnifiedViewDTO, ViewResultDTO


class CommunityFeedUI:
    """
    UI logic for the CommunityFeed feature.
    Responsible for creating views and layouts.
    """

    def render_main(self, payload: Any = None) -> ViewResultDTO | UnifiedViewDTO:
        """
        Renders the main menu/view for the feature.
        """
        return UnifiedViewDTO(text="Hello from CommunityFeed feature!")

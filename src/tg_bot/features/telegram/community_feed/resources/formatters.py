from typing import Any

from .texts import CommunityFeedTexts


class CommunityFeedFormatter:
    """Message formatting logic for the CommunityFeed feature."""

    def format_main(self, payload: Any) -> str:
        """Formats the main screen text."""
        user_name = payload.get("name", "User") if isinstance(payload, dict) else "User"
        return f"{CommunityFeedTexts.TITLE}\n\n{CommunityFeedTexts.DESCRIPTION}\nUser: {user_name}"

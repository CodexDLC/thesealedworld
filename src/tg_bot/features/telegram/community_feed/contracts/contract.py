from typing import Any, Protocol


class CommunityFeedDataProvider(Protocol):
    """
    Contract for accessing CommunityFeed feature data.

    Implementation (Client or Repository) should be registered
    in the BotContainer and injected into the Orchestrator.
    """

    async def get_data(self, user_id: int) -> Any:
        """Example data retrieval method."""
        ...

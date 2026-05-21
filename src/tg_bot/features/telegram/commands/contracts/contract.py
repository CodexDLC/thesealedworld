from typing import Any, Protocol


class AuthDataProvider(Protocol):
    """
    Contract for user authentication and profile management.
    Implementations (API client or Repository) are injected via DI.
    """

    async def upsert_user(self, user_dto: Any) -> None:
        """Create or update user in the system."""
        ...

    async def logout(self, user_id: int) -> None:
        """Clear user session."""
        ...

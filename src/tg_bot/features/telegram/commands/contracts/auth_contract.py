from typing import Any, Protocol


class AuthDataProvider(Protocol):
    """
    Contract for user registration and authentication.
    """

    async def upsert_user(self, user_data: dict[str, Any]) -> None:
        """
        Saves or updates user information in the database or via API.
        """
        ...

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from src.frontend.features.auth.dto.user import UserResponse


class FrontendAuthUserCache(Protocol):
    async def get(self, user_id: uuid.UUID) -> UserResponse | None: ...

    async def set(self, user: UserResponse) -> None: ...

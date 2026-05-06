from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from src.backend.features_site.auth.models import User


class AuthUserCache(Protocol):
    async def get(self, user_id: uuid.UUID) -> User | None: ...

    async def set(self, user: User) -> None: ...

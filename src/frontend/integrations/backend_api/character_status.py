from typing import Any, cast

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CharacterStatusDTO
from src.shared.schemas.character_status import CharacterActorCoreDTO


class BackendCharacterStatusApi(BaseApiClient):
    async def get_actor_core(self, access_token: str, *, char_id: int) -> CharacterActorCoreDTO:
        return await self._request(
            "GET",
            "/character-status/ac",
            response_model=CharacterActorCoreDTO,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"char_id": char_id},
        )

    async def get_panel(self, access_token: str, *, char_id: int) -> CharacterActorCoreDTO:
        return await self._request(
            "GET",
            "/character-status/panel",
            response_model=CharacterActorCoreDTO,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"char_id": char_id},
        )

    async def get_status(self, access_token: str, *, char_id: int) -> CharacterStatusDTO:
        return await self._request(
            "GET",
            "/character-status/status",
            response_model=CharacterStatusDTO,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"char_id": char_id},
        )

    async def update_avatar(self, access_token: str, *, char_id: int, avatar_url: str) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            await self._request(
                "POST",
                "/character-status/avatar",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"char_id": char_id, "avatar_url": avatar_url},
            ),
        )

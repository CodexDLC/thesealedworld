from fastapi import Request

from src.frontend.integrations.backend_api.character_status import BackendCharacterStatusApi
from src.frontend.site_features.auth.token_state import require_access_token
from src.shared.schemas import CharacterStatusDTO
from src.shared.schemas.character_status import CharacterActorCoreDTO


class StatusPanelService:
    def __init__(self, *, api: BackendCharacterStatusApi) -> None:
        self.api = api

    async def get_panel(self, request: Request, *, char_id: int) -> CharacterActorCoreDTO:
        return await self.api.get_panel(require_access_token(request), char_id=char_id)

    async def get_status(self, request: Request, *, char_id: int) -> CharacterStatusDTO:
        return await self.api.get_status(require_access_token(request), char_id=char_id)

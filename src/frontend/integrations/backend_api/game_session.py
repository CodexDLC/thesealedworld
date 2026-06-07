from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO, EnterCharacterRequestDTO, StateTransitionDTO
from src.shared.schemas.game_session import DevStarterRiftResetRequestDTO, StartingImprintOptionsDTO
from src.shared.schemas.loot import LootClaimRequestDTO

GameSessionEnterResponse = CoreResponseDTO[StateTransitionDTO | dict[str, Any]]


class BackendGameSessionApi(BaseApiClient):
    async def enter(self, access_token: str, dto: EnterCharacterRequestDTO) -> GameSessionEnterResponse:
        return await self._request(
            "POST",
            "/game-session/enter",
            response_model=GameSessionEnterResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )

    async def respawn(self, access_token: str, dto: EnterCharacterRequestDTO) -> GameSessionEnterResponse:
        return await self._request(
            "POST",
            "/game-session/respawn",
            response_model=GameSessionEnterResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )

    async def claim_loot(self, access_token: str, dto: LootClaimRequestDTO) -> GameSessionEnterResponse:
        return await self._request(
            "POST",
            "/game-session/loot/claim-all",
            response_model=GameSessionEnterResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )

    async def list_starting_imprints(self) -> StartingImprintOptionsDTO:
        return await self._request(
            "GET",
            "/game-session/dev/starting-imprints",
            response_model=StartingImprintOptionsDTO,
        )

    async def dev_reset_starter_rift(
        self,
        access_token: str,
        dto: DevStarterRiftResetRequestDTO,
    ) -> GameSessionEnterResponse:
        return await self._request(
            "POST",
            "/game-session/dev/starter-rift-reset",
            response_model=GameSessionEnterResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )

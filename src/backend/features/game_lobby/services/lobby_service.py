from src.backend.features.auth.models import User
from src.backend.features.game_lobby.dto.lobby import GameLobbyPayloadDTO, LobbySlotDTO


class GameLobbyService:
    async def get_start_payload(self, _: User) -> GameLobbyPayloadDTO:
        return GameLobbyPayloadDTO(
            slots=[LobbySlotDTO(index=index) for index in range(1, 5)],
        )

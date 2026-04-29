from src.backend.features.game_lobby.services.lobby_service import GameLobbyService


def get_game_lobby_service() -> GameLobbyService:
    return GameLobbyService()

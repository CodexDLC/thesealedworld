from pydantic import BaseModel

from src.shared.schemas.character import CharacterReadDTO


class LobbyListDTO(BaseModel):
    """
    DTO для списка персонажей в лобби.
    """

    characters: list[CharacterReadDTO]

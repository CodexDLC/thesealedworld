from pydantic import BaseModel

from src.shared.schemas import ScenarioPayloadDTO


class ScenarioInitRequestDTO(BaseModel):
    char_id: int
    user_id: str | None = None
    quest_key: str
    source: str = "internal"


class ScenarioInitResponseDTO(BaseModel):
    payload: ScenarioPayloadDTO

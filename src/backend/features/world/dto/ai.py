from pydantic import BaseModel, Field


class WorldLocationTextDTO(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=96)
    description: str = Field(min_length=1, max_length=900)


class WorldLocationBatchResponseDTO(BaseModel):
    locations: list[WorldLocationTextDTO]


class WorldZoneLoreDTO(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    background: str = Field(default="", max_length=1000)

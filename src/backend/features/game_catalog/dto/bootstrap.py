from typing import Any

from pydantic import BaseModel, Field


class GameCatalogManifestDTO(BaseModel):
    version: str
    catalogs: dict[str, str] = Field(default_factory=dict)


class GameCatalogBootstrapDTO(BaseModel):
    version: str
    catalogs: dict[str, dict[str, dict[str, Any]]] = Field(default_factory=dict)
    manifest: GameCatalogManifestDTO

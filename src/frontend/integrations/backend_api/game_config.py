from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.frontend.core.api import BaseApiClient


@dataclass(frozen=True)
class ConfigEntryDTO:
    key: str
    namespace: str
    current: str
    default: str
    value_type: str
    is_modified: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfigEntryDTO:
        return cls(
            key=data["key"],
            namespace=data["namespace"],
            current=data["current"],
            default=data["default"],
            value_type=data.get("value_type", "str"),
            is_modified=data.get("is_modified", False),
        )


class GameConfigApi(BaseApiClient):
    async def list_namespace(self, namespace: str) -> list[ConfigEntryDTO]:
        raw = await self._request("GET", f"/api/internal/config/{namespace}")
        items: list[dict] = raw.get("data", raw) if isinstance(raw, dict) and "data" in raw else raw  # type: ignore[assignment]
        if not isinstance(items, list):
            return []
        return [ConfigEntryDTO.from_dict(item) for item in items]

    async def set_value(self, namespace: str, key: str, value: str) -> None:
        await self._request("PATCH", f"/api/internal/config/{namespace}/{key}", json={"value": value})

    async def reset_key(self, namespace: str, key: str) -> None:
        await self._request("DELETE", f"/api/internal/config/{namespace}/{key}")

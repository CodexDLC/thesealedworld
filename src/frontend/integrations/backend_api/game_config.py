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
    label: str | None = None
    description: str | None = None
    group: str | None = None
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    risk: str = "low"
    live_scope: str = "runtime"
    tags: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfigEntryDTO:
        return cls(
            key=data["key"],
            namespace=data["namespace"],
            current=data["current"],
            default=data["default"],
            value_type=data.get("value_type", "str"),
            is_modified=data.get("is_modified", False),
            label=_optional_str(data.get("label")),
            description=_optional_str(data.get("description")),
            group=_optional_str(data.get("group")),
            unit=_optional_str(data.get("unit")),
            min_value=_optional_float(data.get("min_value")),
            max_value=_optional_float(data.get("max_value")),
            step=_optional_float(data.get("step")),
            risk=str(data.get("risk") or "low"),
            live_scope=str(data.get("live_scope") or "runtime"),
            tags=[str(tag) for tag in data.get("tags", [])] if isinstance(data.get("tags"), list) else [],
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

    async def reset_namespace(self, namespace: str) -> None:
        await self._request("DELETE", f"/api/internal/config/{namespace}")


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float | str) or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

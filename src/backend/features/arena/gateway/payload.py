from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.schemas.arena import ArenaActionDTO


def payload_dict(body: ArenaActionDTO) -> dict[str, Any]:
    return body.value if isinstance(body.value, dict) else {}


def payload_int(body: ArenaActionDTO, key: str, *, default: int) -> int:
    value = payload_dict(body).get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc


def payload_bool(body: ArenaActionDTO, key: str, *, default: bool = False) -> bool:
    value = payload_dict(body).get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def payload_str(body: ArenaActionDTO, key: str) -> str | None:
    value = payload_dict(body).get(key)
    return str(value) if value is not None else None

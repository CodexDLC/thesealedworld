from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class StaticLocationContent(TypedDict):
    title: str
    description: str
    environment_tags: list[str]


class StaticLocation(TypedDict):
    sector_id: str
    is_active: bool
    services: list[str]
    flags: dict[str, Any]
    movement_profile: dict[str, Any]
    node_type: NotRequired[str]
    terrain_type: NotRequired[str]
    content: StaticLocationContent


StaticLocationMap = dict[tuple[int, int], StaticLocation]

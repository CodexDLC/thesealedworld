from __future__ import annotations

from src.backend.features.rift.dto.screen import RiftAbsoluteDirection, RiftCoordinateDTO, RiftRelativeDirection

DIRECTION_OFFSETS: dict[RiftAbsoluteDirection, tuple[int, int]] = {
    "north": (0, -1),
    "east": (1, 0),
    "south": (0, 1),
    "west": (-1, 0),
}

ORDERED_DIRECTIONS: tuple[RiftAbsoluteDirection, ...] = ("north", "east", "south", "west")
OPPOSITE_DIRECTIONS: dict[RiftAbsoluteDirection, RiftAbsoluteDirection] = {
    "north": "south",
    "east": "west",
    "south": "north",
    "west": "east",
}

_RELATIVE_BY_DELTA: dict[int, RiftRelativeDirection] = {
    0: "forward",
    1: "right",
    2: "back",
    3: "left",
}


def neighbor_coord(coord: RiftCoordinateDTO, direction: RiftAbsoluteDirection) -> RiftCoordinateDTO:
    dx, dy = DIRECTION_OFFSETS[direction]
    return RiftCoordinateDTO(x=coord.x + dx, y=coord.y + dy)


def direction_between(source: RiftCoordinateDTO, target: RiftCoordinateDTO) -> RiftAbsoluteDirection | None:
    dx = target.x - source.x
    dy = target.y - source.y
    for direction, offset in DIRECTION_OFFSETS.items():
        if offset == (dx, dy):
            return direction
    return None


def relative_direction(
    *,
    heading: RiftAbsoluteDirection | None,
    direction: RiftAbsoluteDirection,
) -> RiftRelativeDirection | None:
    if heading is None:
        return None
    delta = (ORDERED_DIRECTIONS.index(direction) - ORDERED_DIRECTIONS.index(heading)) % len(ORDERED_DIRECTIONS)
    return _RELATIVE_BY_DELTA[delta]

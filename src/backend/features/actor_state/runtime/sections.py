from src.backend.core.redis.actor_snapshot_manager import ActorSnapshotSection

META: ActorSnapshotSection = "meta"
RUNTIME: ActorSnapshotSection = "runtime"
COMBAT: ActorSnapshotSection = "combat"
INVENTORY: ActorSnapshotSection = "inventory"
STATUS: ActorSnapshotSection = "status"
SOURCE: ActorSnapshotSection = "source"

ALL_SECTIONS: set[ActorSnapshotSection] = {META, RUNTIME, COMBAT, INVENTORY, STATUS, SOURCE}
ALWAYS_SECTIONS: set[ActorSnapshotSection] = {META, SOURCE}


def resolve_sections(include: set[str] | None, exclude: set[str]) -> set[ActorSnapshotSection]:
    selected: set[str] = set(ALL_SECTIONS)
    if include is not None:
        selected &= include
    selected -= exclude
    selected |= ALWAYS_SECTIONS
    return {section for section in selected if section in ALL_SECTIONS}

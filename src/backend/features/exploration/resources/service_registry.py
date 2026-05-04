from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.shared.enums import CoreDomain


@dataclass(frozen=True)
class ExplorationServiceEntry:
    service_id: str
    target_state: CoreDomain
    label: str
    access_policy: str = "public"
    metadata: dict[str, Any] = field(default_factory=dict)


# TODO(service-registry): replace this static mapper with a cold DB model plus
# hot Redis cache and an internal navigation/service-entry integration.
# Location data should expose allowed service_ids; registry/cache should resolve
# service_id -> target domain/ref/access rules. This is required for player
# homes, clan houses, and other private/dynamic buildings.
SERVICE_REGISTRY: dict[str, ExplorationServiceEntry] = {
    "svc_arena_main": ExplorationServiceEntry(
        service_id="svc_arena_main",
        target_state=CoreDomain.ARENA,
        label="На арену",
        metadata={"service_type": "arena"},
    ),
}


def get_service_entry(service_id: str) -> ExplorationServiceEntry | None:
    return SERVICE_REGISTRY.get(service_id)

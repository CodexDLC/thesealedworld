from __future__ import annotations

import pytest

from src.backend.features.rift.resources import RiftResourceLoader
from src.backend.features.rift.runtime.generation import build_zone_runtime
from src.backend.infrastructure.rift.managers import (
    RiftInstanceStore,
    RiftPortalStore,
    RiftPresenceStore,
    RiftRunSessionStore,
)


@pytest.mark.unit
async def test_rift_instance_store_owns_instance_keyspace(fake_redis_service, fake_redis_client) -> None:
    store = RiftInstanceStore(fake_redis_service)
    runtime = _runtime()

    await store.save_instance(runtime)
    loaded = await store.require_instance(runtime.rift_instance_id)
    await store.patch_node_event(runtime.rift_instance_id, runtime.start_node_id, {"event_type": "none"})
    await store.mark_node_cleared(runtime.rift_instance_id, runtime.start_node_id)
    await store.set_gate_state(runtime.rift_instance_id, "gate-1", {"state": "open"})
    await store.set_heart_state(runtime.rift_instance_id, {"state": "alive"})

    key = f"game:rift:instance:{runtime.rift_instance_id}"
    assert loaded.rift_instance_id == runtime.rift_instance_id
    assert f"game:rift:runtime:{runtime.rift_instance_id}" not in fake_redis_client.store
    assert key in fake_redis_client.store
    assert fake_redis_client.ttls[key] == RiftInstanceStore.DEFAULT_TTL_SECONDS
    assert fake_redis_client.store[key]["node_events"][runtime.start_node_id] == {"event_type": "none"}
    assert fake_redis_client.store[key]["node_states"][runtime.start_node_id]["cleared"] is True
    assert fake_redis_client.store[key]["gate_states"]["gate-1"] == {"state": "open"}
    assert fake_redis_client.store[key]["heart_state"] == {"state": "alive"}


@pytest.mark.unit
async def test_rift_run_session_store_owns_session_keyspace(fake_redis_service, fake_redis_client) -> None:
    store = RiftRunSessionStore(fake_redis_service)
    payload = {
        "rift_session_id": "rfs-1",
        "owner_type": "solo",
        "owner_id": "char:7",
        "rift_instance_id": "rift-1",
        "zone_instance_id": "zone-1",
        "current_node_id": "z01:0_0",
        "visited_node_ids": ["z01:0_0"],
    }

    await store.create_session(payload)
    assert await store.scan_dirty(limit=10) == []
    await store.set_position("rfs-1", current_node_id="z01:1_0", previous_node_id="z01:0_0", heading="east")
    await store.set_visited("rfs-1", {"z01:0_0", "z01:1_0"})
    await store.set_discovered("rfs-1", {"z01:0_0", "z01:1_0", "z01:2_0"})
    await store.start_travel("rfs-1", {"travel_id": "trv-1", "status": "moving"})
    await store.interrupt_travel("rfs-1", {"travel_id": "trv-1"})
    await store.complete_travel("rfs-1", last_travel={"event_type": "combat"})
    await store.set_active_encounter("rfs-1", "enc-1")
    await store.clear_active_encounter("rfs-1")
    loaded = await store.require_session("rfs-1")

    key = "game:rift:session:rfs-1"
    assert key in fake_redis_client.store
    assert fake_redis_client.ttls[key] == RiftRunSessionStore.DEFAULT_TTL_SECONDS
    assert loaded["current_node_id"] == "z01:1_0"
    assert loaded["previous_node_id"] == "z01:0_0"
    assert loaded["heading"] == "east"
    assert loaded["visited_node_ids"] == ["z01:0_0", "z01:1_0"]
    assert loaded["discovered_node_ids"] == ["z01:0_0", "z01:1_0", "z01:2_0"]
    assert loaded["active_travel"] is None
    assert loaded["last_travel"] == {"event_type": "combat"}
    assert loaded["active_encounter_id"] is None
    assert loaded["is_dirty"] is True
    assert loaded["dirty"]["reason"] == "active_encounter_cleared"
    assert await store.scan_dirty(limit=10) == ["rfs-1"]

    await store.clear_dirty("rfs-1")
    clean = await store.require_session("rfs-1")
    assert clean["is_dirty"] is False
    assert clean["dirty"]["dirty"] is False
    assert await store.scan_dirty(limit=10) == []


@pytest.mark.unit
async def test_rift_presence_store_owns_presence_keyspaces() -> None:
    redis = _PresenceRedisService()
    store = RiftPresenceStore(redis)

    await store.enter_node("rift-1", "z01:0_0", "char:7")
    await store.move_node("rift-1", from_node_id="z01:0_0", to_node_id="z01:1_0", participant_ref="char:7")
    await store.join_travel("rift-1", "trv-1", "char:7")
    await store.join_encounter("rift-1", "enc-1", "char:7")

    assert await store.get_node_occupants("rift-1", "z01:0_0") == set()
    assert await store.get_node_occupants("rift-1", "z01:1_0") == {"char:7"}
    assert await store.get_travel_participants("rift-1", "trv-1") == {"char:7"}
    assert await store.get_encounter_participants("rift-1", "enc-1") == {"char:7"}
    assert redis.ttls["game:rift:presence:rift-1:node:z01:1_0"] == RiftPresenceStore.DEFAULT_TTL_SECONDS
    assert redis.ttls["game:rift:presence:rift-1:travel:trv-1"] == RiftPresenceStore.DEFAULT_TTL_SECONDS
    assert redis.ttls["game:rift:presence:rift-1:encounter:enc-1"] == RiftPresenceStore.DEFAULT_TTL_SECONDS

    await store.clear_node_presence("rift-1", "z01:1_0")
    assert await store.get_node_occupants("rift-1", "z01:1_0") == set()


@pytest.mark.unit
async def test_rift_portal_store_tracks_and_archives_portal_keys(fake_redis_service, fake_redis_client) -> None:
    store = RiftPortalStore(fake_redis_service)

    created = await store.save_portal(
        {
            "portal_id": "portal-1",
            "rift_session_id": "rift:run:1",
            "rift_instance_id": "rift-1",
            "owner_id": "char:7",
            "status": "active",
            "expires_at": 10.0,
        }
    )
    linked = await store.find_by_rift_session("rift:run:1")
    archived = await store.archive_due(now=11.0, limit=10)

    key = "game:rift:portal:portal-1"
    assert created["status"] == "active"
    assert linked is not None and linked["portal_id"] == "portal-1"
    assert key in fake_redis_client.store
    assert fake_redis_client.ttls[key] == RiftPortalStore.DEFAULT_TTL_SECONDS
    assert archived[0]["portal_id"] == "portal-1"
    assert archived[0]["status"] == "archived"
    assert archived[0]["status_reason"] == "expired"


def _runtime():
    resources = RiftResourceLoader()
    return build_zone_runtime(
        setting=resources.load_setting("starter_rift"),
        pool_nodes=resources.load_node_pool("starter_rift"),
        scale_preset=resources.load_scale_presets()["medium"],
        assembly_preset=resources.load_zone_assembly_presets()["grid_5x5_active_15"],
        seed="redis-store-check",
        debug=True,
    )


class _PresenceRedisClient:
    def __init__(self) -> None:
        self.sets: dict[str, set[str]] = {}
        self.ttls: dict[str, int] = {}

    async def sadd(self, key: str, value: str) -> None:
        self.sets.setdefault(key, set()).add(value)

    async def srem(self, key: str, value: str) -> None:
        self.sets.setdefault(key, set()).discard(value)

    async def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    async def expire(self, key: str, ttl: int) -> None:
        self.ttls[key] = ttl

    async def delete(self, key: str) -> None:
        self.sets.pop(key, None)
        self.ttls.pop(key, None)


class _PresenceRedisService:
    def __init__(self) -> None:
        self.redis_client = _PresenceRedisClient()

    @property
    def ttls(self) -> dict[str, int]:
        return self.redis_client.ttls

    @property
    def sets(self) -> dict[str, set[str]]:
        return self.redis_client.sets

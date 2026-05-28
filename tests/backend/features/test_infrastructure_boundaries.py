from __future__ import annotations

import importlib
from pathlib import Path


def test_expedition_redis_manager_is_in_infrastructure() -> None:
    module = importlib.import_module("src.backend.infrastructure.expedition.managers")

    assert hasattr(module, "ExpeditionRedisManager")
    assert not Path("src/backend/features/expedition/redis_manager.py").exists()


def test_arena_session_manager_owns_arena_redis_runtime() -> None:
    module = importlib.import_module("src.backend.infrastructure.arena.managers")

    assert hasattr(module, "ArenaSessionManager")
    assert not Path("src/backend/features/arena/repositories/session_store.py").exists()


def test_inventory_session_manager_owns_inventory_redis_runtime() -> None:
    module = importlib.import_module("src.backend.infrastructure.inventory.managers")

    assert hasattr(module, "InventorySessionManager")
    assert not Path("src/backend/features/inventory/services/session_manager.py").exists()


def test_character_session_manager_is_in_infrastructure() -> None:
    module = importlib.import_module("src.backend.infrastructure.actor_state.managers")

    assert hasattr(module, "CharacterSessionManager")
    assert not Path("src/backend/features/character/managers/session.py").exists()


def test_exploration_redis_managers_are_in_infrastructure() -> None:
    module = importlib.import_module("src.backend.infrastructure.exploration.managers")

    assert hasattr(module, "ExplorationEncounterRuntimeManager")
    assert hasattr(module, "ExplorationKnowledgeRuntimeManager")
    assert not Path("src/backend/features/exploration/services/knowledge_runtime.py").exists()


def test_monster_redis_managers_are_in_infrastructure() -> None:
    module = importlib.import_module("src.backend.infrastructure.monsters.managers")

    assert hasattr(module, "MonsterGroupCacheManager")
    assert hasattr(module, "AnchorProjectionSnapshotCacheManager")
    assert not Path("src/backend/features/monsters/integrations/group_cache.py").exists()


def test_rift_redis_managers_are_in_infrastructure() -> None:
    module = importlib.import_module("src.backend.infrastructure.rift.managers")

    assert hasattr(module, "RiftInstanceStore")
    assert hasattr(module, "RiftRunSessionStore")
    assert hasattr(module, "RiftPresenceStore")
    assert not list(Path("src/backend/features/rift/redis").glob("*.py"))


def test_features_do_not_build_inventory_redis_keys() -> None:
    offenders = []
    for path in Path("src/backend/features").rglob("*.py"):
        if "rift" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        forbidden_prefixes = (
            "game:inventory:",
            "game:encounter:",
            "game:exploration:knowledge",
            "game:monster:",
            "loot:pending",
            "combat:announcement:",
        )
        if any(prefix in text for prefix in forbidden_prefixes):
            offenders.append(path.as_posix())

    assert offenders == []

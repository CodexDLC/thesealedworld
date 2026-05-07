from fastapi_cabinet import CabinetAdmin, CabinetRegistry
from fastapi_cabinet.runtime import admin_public_path, admin_route_path, resolve_active_admin


class WorldAdmin(CabinetAdmin):
    key = "world"
    label = "World"


class CharacterAdmin(CabinetAdmin):
    key = "character"
    label = "Character"
    path = "/cabinet/world/characters"


def test_active_module_is_resolved_by_path_prefix() -> None:
    registry = CabinetRegistry()
    registry.register(WorldAdmin)
    registry.register(CharacterAdmin)

    active = resolve_active_admin("/cabinet/world/characters/42", registry)

    assert active is not None
    assert active.key == "character"


def test_admin_paths_default_under_mount_path() -> None:
    admin = WorldAdmin()

    assert admin_public_path(admin) == "/cabinet/world"
    assert admin_route_path(admin) == "/world"

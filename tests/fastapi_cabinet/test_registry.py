import pytest

from fastapi_cabinet import CabinetAdmin, CabinetRegistry
from fastapi_cabinet.exceptions import CabinetDuplicateKeyError


class WorldAdmin(CabinetAdmin):
    key = "world"
    label = "World"


def test_registry_stores_registered_admin_class() -> None:
    registry = CabinetRegistry()

    registered = registry.register(WorldAdmin)

    assert registered.key == "world"
    assert registry.get("world") is registered
    assert registry.all() == (registered,)


def test_duplicate_module_keys_fail_clearly() -> None:
    registry = CabinetRegistry()
    registry.register(WorldAdmin)

    with pytest.raises(CabinetDuplicateKeyError, match="world"):
        registry.register(WorldAdmin)

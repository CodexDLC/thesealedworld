import sys
from types import ModuleType

import pytest

from fastapi_cabinet import CabinetAdmin, CabinetSite, cabinet_site
from fastapi_cabinet.exceptions import CabinetModuleLoadError
from fastapi_cabinet.loader import load_cabinet_modules


class WorldAdmin(CabinetAdmin):
    key = "world"
    label = "World"


def test_imported_module_ref_can_register_with_hook() -> None:
    module = ModuleType("cabinet_module")

    def register_cabinet(registry: object) -> None:
        registry.register(WorldAdmin)  # type: ignore[attr-defined]

    module.__dict__["register_cabinet"] = register_cabinet
    site = CabinetSite()

    loaded = load_cabinet_modules((module,), site)

    assert loaded == (module,)
    assert site.registry.get("world").label == "World"


def test_string_module_ref_can_register_with_hook(tmp_path) -> None:
    module_path = tmp_path / "world_cabinet.py"
    module_path.write_text(
        "\n".join(
            [
                "from fastapi_cabinet import CabinetAdmin",
                "class WorldAdmin(CabinetAdmin):",
                "    key = 'world'",
                "    label = 'World'",
                "def register_cabinet(registry):",
                "    registry.register(WorldAdmin)",
            ]
        ),
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        site = CabinetSite()
        load_cabinet_modules(("world_cabinet",), site)
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("world_cabinet", None)

    assert site.registry.get("world").label == "World"


def test_import_time_global_site_registration_style(tmp_path) -> None:
    module_path = tmp_path / "global_cabinet.py"
    module_path.write_text(
        "\n".join(
            [
                "from fastapi_cabinet import CabinetAdmin, cabinet_site",
                "class GlobalAdmin(CabinetAdmin):",
                "    key = 'global_test_module'",
                "    label = 'Global'",
                "cabinet_site.register(GlobalAdmin)",
            ]
        ),
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        load_cabinet_modules(("global_cabinet",), cabinet_site)
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("global_cabinet", None)

    assert cabinet_site.registry.get("global_test_module").label == "Global"


def test_missing_module_fails_clearly() -> None:
    with pytest.raises(CabinetModuleLoadError, match="does_not_exist"):
        load_cabinet_modules(("does_not_exist",), CabinetSite())


def test_invalid_hook_fails_clearly() -> None:
    module = ModuleType("bad_cabinet_module")

    def register_cabinet() -> None:
        return None

    module.__dict__["register_cabinet"] = register_cabinet

    with pytest.raises(CabinetModuleLoadError, match="exactly one registry"):
        load_cabinet_modules((module,), CabinetSite())

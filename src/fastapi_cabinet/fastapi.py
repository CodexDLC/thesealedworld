from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from fastapi_cabinet.loader import load_cabinet_modules
from fastapi_cabinet.site import CabinetSite, cabinet_site

CabinetModuleRef = str | ModuleType


def include_cabinet(
    app: FastAPI,
    *,
    modules: Sequence[CabinetModuleRef],
    mount_path: str = "/cabinet",
    static_mount_path: str | None = None,
    site: CabinetSite | None = None,
) -> CabinetSite:
    active_site = site or cabinet_site
    load_cabinet_modules(modules, active_site)
    resolved_static_mount_path = static_mount_path or f"{mount_path.rstrip('/')}/static"
    active_site.static_mount_path = resolved_static_mount_path
    app.include_router(active_site.build_router(mount_path=mount_path, static_mount_path=resolved_static_mount_path))
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount(resolved_static_mount_path, StaticFiles(directory=static_dir), name="fastapi_cabinet_static")
    return active_site

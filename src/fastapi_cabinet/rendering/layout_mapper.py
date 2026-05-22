from pathlib import Path

from fastapi_cabinet.contracts.admin import CabinetAdmin
from fastapi_cabinet.contracts.layout import CabinetLayoutMap, HeaderGroup
from fastapi_cabinet.contracts.navigation import HeaderItem
from fastapi_cabinet.registry import CabinetRegistry
from fastapi_cabinet.runtime import admin_public_path

_STATIC_DIR = Path(__file__).parents[1] / "static"


def build_layout_map(
    registry: CabinetRegistry,
    *,
    mount_path: str,
    active_admin: CabinetAdmin | None,
    static_mount_path: str | None = None,
    active_path: str = "",
    sidebar_badges: dict[str, int | str] | None = None,
    title: str = "Cabinet",
) -> CabinetLayoutMap:
    header = [
        HeaderItem(
            key=admin.key,
            label=admin.label,
            path=admin_public_path(admin, mount_path),
            icon=admin.icon,
            group=admin.group,
            group_label=admin.group_label,
            order=admin.order,
        )
        for admin in registry.all()
    ]
    header = sorted(header, key=lambda item: (item.order, item.key))
    header_groups = _build_header_groups(header)
    sidebar = list(active_admin.sidebar) if active_admin else []
    return CabinetLayoutMap(
        mount_path=mount_path,
        static_mount_path=(static_mount_path or f"{mount_path.rstrip('/')}/static"),
        static_version=_static_version(),
        title=title,
        active_module=active_admin.key if active_admin else None,
        active_path=active_path,
        header=header,
        header_groups=header_groups,
        sidebar=sorted(sidebar, key=lambda item: (item.order, item.key)),
        sidebar_badges=sidebar_badges or {},
        notification_count=0,
    )


def _build_header_groups(header: list[HeaderItem]) -> list[HeaderGroup]:
    seen: dict[str, HeaderGroup] = {}
    for item in header:
        group_key = item.group
        if group_key not in seen:
            seen[group_key] = HeaderGroup(
                key=group_key,
                label=item.group_label or group_key,
                items=[],
            )
        seen[group_key].items.append(item)
    return list(seen.values())


def _static_version() -> str:
    asset_paths = (
        _STATIC_DIR / "css" / "cabinet.css",
        _STATIC_DIR / "js" / "cabinet.js",
    )
    mtimes = []
    for path in asset_paths:
        try:
            mtimes.append(int(path.stat().st_mtime))
        except OSError:
            mtimes.append(0)
    return str(max(mtimes))

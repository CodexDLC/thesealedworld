from fastapi_cabinet.contracts.admin import CabinetAdmin
from fastapi_cabinet.contracts.layout import CabinetLayoutMap
from fastapi_cabinet.contracts.navigation import HeaderItem
from fastapi_cabinet.registry import CabinetRegistry
from fastapi_cabinet.runtime import admin_public_path


def build_layout_map(
    registry: CabinetRegistry,
    *,
    mount_path: str,
    active_admin: CabinetAdmin | None,
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
            order=admin.order,
        )
        for admin in registry.all()
    ]
    sidebar = list(active_admin.sidebar) if active_admin else []
    return CabinetLayoutMap(
        mount_path=mount_path,
        title=title,
        active_module=active_admin.key if active_admin else None,
        header=sorted(header, key=lambda item: (item.order, item.key)),
        sidebar=sorted(sidebar, key=lambda item: (item.order, item.key)),
        sidebar_badges=sidebar_badges or {},
    )

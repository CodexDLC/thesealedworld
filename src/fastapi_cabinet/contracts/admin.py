from typing import ClassVar

from fastapi import Request

from fastapi_cabinet.contracts.navigation import SidebarItem
from fastapi_cabinet.contracts.providers import WidgetProvider
from fastapi_cabinet.contracts.widgets import DashboardWidget


class CabinetAdmin:
    key: ClassVar[str]
    label: ClassVar[str]
    icon: ClassVar[str] = ""
    path: ClassVar[str | None] = None
    group: ClassVar[str] = "main"
    group_label: ClassVar[str] = ""
    order: ClassVar[int] = 100

    sidebar: ClassVar[tuple[SidebarItem, ...]] = ()
    dashboard_widgets: ClassVar[tuple[DashboardWidget, ...]] = ()
    sub_pages: ClassVar[dict[str, tuple[DashboardWidget, ...]]] = {}
    providers: ClassVar[dict[str, WidgetProvider]] = {}
    action_routes: ClassVar[dict[str, tuple[str, str]]] = {}
    # format: {"url_suffix": ("HTTP_METHOD", "method_name_on_admin_instance")}

    async def get_dashboard_context(self, request: Request) -> dict[str, object]:
        return {}

    async def get_sidebar_badges(self, request: Request) -> dict[str, int | str]:
        return {}

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse, Response

from fastapi_cabinet.contracts.admin import CabinetAdmin
from fastapi_cabinet.contracts.widgets import DashboardWidget
from fastapi_cabinet.registry import CabinetRegistry
from fastapi_cabinet.rendering.layout_mapper import build_layout_map
from fastapi_cabinet.rendering.widget_mapper import resolve_admin_widgets
from fastapi_cabinet.runtime import admin_public_path, admin_route_path, resolve_active_admin


class CabinetSite:
    def __init__(self) -> None:
        self.registry = CabinetRegistry()
        self.templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

    def register(self, admin: type[CabinetAdmin] | CabinetAdmin) -> CabinetAdmin:
        return self.registry.register(admin)

    def build_router(self, mount_path: str = "/cabinet") -> APIRouter:
        router = APIRouter(prefix=mount_path.rstrip("/"))

        @router.get("")
        async def dashboard(request: Request) -> Response:
            admins = self.registry.all()
            if admins:
                return RedirectResponse(url=admin_public_path(admins[0], mount_path))
            layout = build_layout_map(
                self.registry,
                mount_path=mount_path,
                active_admin=None,
                active_path=str(request.url.path),
            )
            return self.templates.TemplateResponse(
                request,
                "cabinet/dashboard.html",
                {"layout": layout, "modules": [], "widgets": []},
            )

        for admin in self.registry.all():
            router.get(admin_route_path(admin, mount_path), name=f"cabinet:{admin.key}")(
                self._build_module_endpoint(admin, mount_path)
            )
            for suffix, page_widgets in admin.sub_pages.items():
                sub_route = f"{admin_route_path(admin, mount_path)}/{suffix}"
                router.get(sub_route, name=f"cabinet:{admin.key}:{suffix}")(
                    self._build_subpage_endpoint(admin, suffix, page_widgets, mount_path)
                )
            for suffix, (method, handler_name) in admin.action_routes.items():
                action_route = f"{admin_route_path(admin, mount_path)}/{suffix}"
                handler = getattr(admin, handler_name)
                getattr(router, method.lower())(action_route, name=f"cabinet:{admin.key}:action:{suffix}")(handler)

        return router

    def _build_module_endpoint(
        self,
        admin: CabinetAdmin,
        mount_path: str,
    ) -> Callable[[Request], Awaitable[Response]]:
        async def module_page(request: Request) -> Response:
            active_admin = resolve_active_admin(request.url.path, self.registry, mount_path)
            sidebar_badges = await admin.get_sidebar_badges(request)
            layout = build_layout_map(
                self.registry,
                mount_path=mount_path,
                active_admin=active_admin,
                active_path=str(request.url.path),
                sidebar_badges=sidebar_badges,
                title=admin.label,
            )
            module_context = await admin.get_dashboard_context(request)
            return self.templates.TemplateResponse(
                request,
                "cabinet/module.html",
                {
                    "layout": layout,
                    "module": admin,
                    "module_context": module_context,
                    "widgets": await resolve_admin_widgets(admin, admin.dashboard_widgets, request),
                },
            )

        return module_page

    def _build_subpage_endpoint(
        self,
        admin: CabinetAdmin,
        suffix: str,
        page_widgets: tuple[DashboardWidget, ...],
        mount_path: str,
    ) -> Callable[[Request], Awaitable[Response]]:
        async def subpage(request: Request) -> Response:
            active_admin = resolve_active_admin(request.url.path, self.registry, mount_path)
            sidebar_badges = await admin.get_sidebar_badges(request)
            layout = build_layout_map(
                self.registry,
                mount_path=mount_path,
                active_admin=active_admin,
                active_path=str(request.url.path),
                sidebar_badges=sidebar_badges,
                title=admin.label,
            )
            return self.templates.TemplateResponse(
                request,
                "cabinet/module.html",
                {
                    "layout": layout,
                    "module": admin,
                    "module_context": {},
                    "widgets": await resolve_admin_widgets(admin, page_widgets, request),
                },
            )

        return subpage


cabinet_site = CabinetSite()

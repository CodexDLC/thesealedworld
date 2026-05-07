from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from fastapi_cabinet.contracts.admin import CabinetAdmin
from fastapi_cabinet.registry import CabinetRegistry
from fastapi_cabinet.rendering.layout_mapper import build_layout_map
from fastapi_cabinet.rendering.widget_mapper import resolve_dashboard_widgets
from fastapi_cabinet.runtime import admin_route_path, resolve_active_admin


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
            active_admin = resolve_active_admin(request.url.path, self.registry, mount_path)
            layout = build_layout_map(self.registry, mount_path=mount_path, active_admin=active_admin)
            return self.templates.TemplateResponse(
                request,
                "cabinet/dashboard.html",
                {
                    "layout": layout,
                    "modules": self.registry.all(),
                    "widgets": await resolve_dashboard_widgets(self.registry.all(), request),
                },
            )

        for admin in self.registry.all():
            router.get(admin_route_path(admin, mount_path), name=f"cabinet:{admin.key}")(
                self._build_module_endpoint(admin, mount_path)
            )

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
                    "widgets": await resolve_dashboard_widgets((admin,), request),
                },
            )

        return module_page


cabinet_site = CabinetSite()

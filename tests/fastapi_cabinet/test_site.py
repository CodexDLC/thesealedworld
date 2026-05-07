from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from fastapi_cabinet import CabinetAdmin, CabinetSite, MetricWidget, SidebarItem, cabinet_site, include_cabinet
from fastapi_cabinet.contracts.widgets import MetricWidgetMap


async def online_provider(request: Request) -> MetricWidgetMap:
    return MetricWidgetMap(key="online", title="Online Players", value="12")


class WorldAdmin(CabinetAdmin):
    key = "world"
    label = "World"
    path = "/cabinet/world"
    sidebar = (SidebarItem(key="overview", label="Overview", path="/cabinet/world", badge_key="overview"),)
    dashboard_widgets = (MetricWidget(key="online", title="Online Players", provider="world.online"),)
    providers: ClassVar = {"world.online": online_provider}

    async def get_sidebar_badges(self, request: Request) -> dict[str, int | str]:
        return {"overview": 7}


def test_cabinet_site_exists_and_registers_admin() -> None:
    site = CabinetSite()

    site.register(WorldAdmin)

    assert site.registry.get("world").label == "World"


def test_global_cabinet_site_exists() -> None:
    assert isinstance(cabinet_site, CabinetSite)


def test_include_cabinet_adds_dashboard_route() -> None:
    app = FastAPI()
    site = CabinetSite()
    site.register(WorldAdmin)

    returned_site = include_cabinet(app, modules=(), site=site)

    response = TestClient(app).get("/cabinet")
    assert returned_site is site
    assert response.status_code == 200
    assert "World" in response.text
    assert "Online Players" in response.text
    assert "12" in response.text


def test_registered_module_path_returns_200() -> None:
    app = FastAPI()
    site = CabinetSite()
    site.register(WorldAdmin)

    include_cabinet(app, modules=(), site=site)

    response = TestClient(app).get("/cabinet/world")
    assert response.status_code == 200
    assert "World" in response.text
    assert "Overview" in response.text
    assert "7" in response.text


def test_cabinet_static_assets_are_mounted() -> None:
    app = FastAPI()

    include_cabinet(app, modules=(), site=CabinetSite())

    response = TestClient(app).get("/cabinet/static/css/cabinet.css")
    assert response.status_code == 200
    assert ".fc-shell" in response.text

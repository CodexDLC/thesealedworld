import pytest
from fastapi import Request

from fastapi_cabinet import CabinetAdmin, MetricWidget
from fastapi_cabinet.contracts.widgets import MetricWidgetMap
from fastapi_cabinet.exceptions import CabinetProviderError
from fastapi_cabinet.rendering.widget_mapper import resolve_dashboard_widgets


async def online_provider(request: Request) -> MetricWidgetMap:
    return MetricWidgetMap(key="online", title="Online Players", value="12")


class WidgetAdmin(CabinetAdmin):
    key = "widgets"
    label = "Widgets"
    dashboard_widgets = (MetricWidget(key="online", title="Online Players", provider="widgets.online"),)
    providers = {"widgets.online": online_provider}


class MissingProviderAdmin(CabinetAdmin):
    key = "missing"
    label = "Missing"
    dashboard_widgets = (MetricWidget(key="missing", title="Missing", provider="widgets.missing"),)


async def test_provider_key_resolves_to_async_callable() -> None:
    widgets = await resolve_dashboard_widgets((WidgetAdmin(),), Request({"type": "http"}))

    assert widgets == [MetricWidgetMap(key="online", title="Online Players", value="12")]


async def test_bad_provider_key_fails_clearly() -> None:
    with pytest.raises(CabinetProviderError, match="widgets.missing"):
        await resolve_dashboard_widgets((MissingProviderAdmin(),), Request({"type": "http"}))

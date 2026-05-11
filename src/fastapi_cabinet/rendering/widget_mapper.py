from collections.abc import Sequence
from typing import Any, cast

from fastapi import Request
from pydantic import BaseModel, ValidationError

from fastapi_cabinet.contracts.admin import CabinetAdmin
from fastapi_cabinet.contracts.providers import WidgetMap
from fastapi_cabinet.contracts.widgets import DashboardWidget, ListWidgetMap, MetricWidgetMap, TableWidgetMap
from fastapi_cabinet.exceptions import CabinetProviderError


async def resolve_admin_widgets(
    admin: CabinetAdmin, widgets: tuple[DashboardWidget, ...], request: Request
) -> list[WidgetMap]:
    result: list[WidgetMap] = []
    for declaration in sorted(widgets, key=lambda w: (w.order, w.key)):
        result.append(await resolve_widget(admin, declaration, request))
    return result


async def resolve_dashboard_widgets(admins: Sequence[CabinetAdmin], request: Request) -> list[WidgetMap]:
    widgets: list[WidgetMap] = []
    for admin in admins:
        for declaration in sorted(admin.dashboard_widgets, key=lambda widget: (widget.order, widget.key)):
            widgets.append(await resolve_widget(admin, declaration, request))
    return widgets


async def resolve_widget(admin: CabinetAdmin, declaration: DashboardWidget, request: Request) -> WidgetMap:
    provider = admin.providers.get(declaration.provider)
    if provider is None:
        raise CabinetProviderError(
            f"Provider {declaration.provider!r} is not registered for cabinet admin {admin.key!r}."
        )
    result = await provider(request)
    return validate_widget_map(declaration, result)


def validate_widget_map(declaration: DashboardWidget, widget: WidgetMap | dict[str, Any]) -> WidgetMap:
    model = _model_for_kind(declaration.kind)
    try:
        return cast("WidgetMap", model.model_validate(widget))
    except ValidationError as exc:
        raise CabinetProviderError(
            f"Provider {declaration.provider!r} returned an invalid {declaration.kind!r} widget map."
        ) from exc


def _model_for_kind(kind: str) -> type[BaseModel]:
    if kind == "metric":
        return MetricWidgetMap
    if kind == "table":
        return TableWidgetMap
    if kind == "list":
        return ListWidgetMap
    raise CabinetProviderError(f"Unsupported dashboard widget kind {kind!r}.")

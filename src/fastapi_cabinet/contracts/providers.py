from collections.abc import Awaitable, Callable

from fastapi import Request

from fastapi_cabinet.contracts.widgets import ListWidgetMap, MetricWidgetMap, TableWidgetMap

type WidgetMap = MetricWidgetMap | TableWidgetMap | ListWidgetMap
type WidgetProvider = Callable[[Request], Awaitable[WidgetMap]]

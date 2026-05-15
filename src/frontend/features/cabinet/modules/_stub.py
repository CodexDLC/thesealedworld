"""Shared stub provider factory for cabinet modules pending real data connections."""

from collections.abc import Callable

from fastapi import Request

from fastapi_cabinet.contracts.widgets import MetricWidgetMap, TableColumnMap, TableWidgetMap


def stub_metric(key: str, title: str, note: str = "подключение позже") -> Callable:
    async def provider(request: Request) -> MetricWidgetMap:
        return MetricWidgetMap(key=key, title=title, value="—", subtitle=note)

    return provider


def stub_table(key: str, title: str, columns: list[str], note: str = "подключение позже") -> Callable:
    async def provider(request: Request) -> TableWidgetMap:
        return TableWidgetMap(
            key=key,
            title=title,
            columns=[TableColumnMap(key=c, label=c) for c in columns],
            rows=[{"—": note}],
        )

    return provider

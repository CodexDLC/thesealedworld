from fastapi import Request

from fastapi_cabinet.contracts import (
    AllowAllPermissionProvider,
    CabinetLayoutMap,
    HeaderItem,
    MetricWidgetMap,
    SidebarItem,
    TableColumnMap,
    TableWidgetMap,
)


def test_navigation_contracts_validate() -> None:
    sidebar = SidebarItem(key="overview", label="Overview", path="/cabinet/world")
    header = HeaderItem(key="world", label="World", path="/cabinet/world", order=10)

    layout = CabinetLayoutMap(
        mount_path="/cabinet",
        title="Cabinet",
        active_module="world",
        header=[header],
        sidebar=[sidebar],
    )

    assert layout.header[0].key == "world"
    assert layout.sidebar[0].order == 100


def test_widget_maps_validate() -> None:
    metric = MetricWidgetMap(key="online", title="Online", value="12")
    table = TableWidgetMap(
        key="nodes",
        title="Nodes",
        columns=[TableColumnMap(key="name", label="Name")],
        rows=[{"name": "Village"}],
    )

    assert metric.kind == "metric"
    assert table.rows == [{"name": "Village"}]


async def test_allow_all_permission_provider_allows_any_permission() -> None:
    provider = AllowAllPermissionProvider()

    assert await provider.can(Request({"type": "http"}), "cabinet.view")

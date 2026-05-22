from fastapi_cabinet import CabinetAdmin, CabinetRegistry, SidebarItem
from fastapi_cabinet.rendering.layout_mapper import build_layout_map


class LaterAdmin(CabinetAdmin):
    key = "later"
    label = "Later"
    order = 20


class FirstAdmin(CabinetAdmin):
    key = "first"
    label = "First"
    order = 10
    sidebar = (
        SidebarItem(key="second", label="Second", path="/cabinet/first/second", order=20, badge_key="second"),
        SidebarItem(key="first", label="First", path="/cabinet/first", order=10),
    )


def test_layout_mapper_sorts_header_and_sidebar() -> None:
    registry = CabinetRegistry()
    later = registry.register(LaterAdmin)
    first = registry.register(FirstAdmin)

    layout = build_layout_map(
        registry,
        mount_path="/cabinet",
        active_admin=first,
        sidebar_badges={"second": 5},
    )

    assert [item.key for item in layout.header] == [first.key, later.key]
    assert layout.static_mount_path == "/cabinet/static"
    assert layout.static_version != "0"
    assert [item.key for item in layout.sidebar] == ["first", "second"]
    assert layout.sidebar_badges == {"second": 5}

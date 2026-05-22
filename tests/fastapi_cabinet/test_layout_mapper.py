import os

from fastapi_cabinet import CabinetAdmin, CabinetRegistry, SidebarItem
from fastapi_cabinet.rendering import layout_mapper
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


def test_static_version_is_cached_per_process(tmp_path, monkeypatch) -> None:
    static_dir = tmp_path / "static"
    css = static_dir / "css" / "cabinet.css"
    js = static_dir / "js" / "cabinet.js"
    css.parent.mkdir(parents=True)
    js.parent.mkdir(parents=True)
    css.write_text("css")
    js.write_text("js")
    os.utime(css, (100, 100))
    os.utime(js, (100, 100))
    monkeypatch.setattr(layout_mapper, "_STATIC_DIR", static_dir)
    layout_mapper._static_version.cache_clear()

    first_version = layout_mapper._static_version()
    os.utime(css, (200, 200))
    second_version = layout_mapper._static_version()

    assert first_version == "100"
    assert second_version == first_version
    layout_mapper._static_version.cache_clear()

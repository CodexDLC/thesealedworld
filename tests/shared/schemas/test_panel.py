from src.shared.schemas.panel import PanelDTO, PanelWidgetDTO


def test_panel_dto_accepts_common_widget_shapes():
    panel = PanelDTO(
        id="status",
        title="STATUS",
        widgets=[
            PanelWidgetDTO(type="avatar", data={"name": "Ada"}),
            PanelWidgetDTO(type="vitals", items=[{"label": "HP", "cur": 10, "max": 12}]),
            PanelWidgetDTO(type="meter_list", items=[{"label": "STR", "value": 8, "max": 20}]),
            PanelWidgetDTO(type="list", items=[{"label": "Bleeding"}]),
            PanelWidgetDTO(type="key_value", items=[{"key": "State", "value": "EXPLORATION"}]),
        ],
    )

    assert panel.widgets[0].type == "avatar"
    assert panel.widgets[2].items[0]["label"] == "STR"

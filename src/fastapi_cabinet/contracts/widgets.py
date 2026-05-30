from typing import Any

from pydantic import BaseModel, Field


class DashboardWidget(BaseModel):
    key: str
    title: str
    provider: str
    kind: str
    order: int = 100


class MetricWidget(DashboardWidget):
    kind: str = "metric"
    icon: str = ""


class TableWidget(DashboardWidget):
    kind: str = "table"


class ListWidget(DashboardWidget):
    kind: str = "list"


class MetricWidgetMap(BaseModel):
    kind: str = "metric"
    key: str
    title: str
    value: str
    subtitle: str | None = None
    trend: str | None = None
    icon: str = ""


class TableColumnMap(BaseModel):
    key: str
    label: str
    align: str = "left"


class TableActionMap(BaseModel):
    action: str
    label: str
    css_class: str = ""
    select_name: str | None = None
    select_options_key: str | None = None
    select_label: str | None = None
    input_name: str | None = None
    input_value_key: str | None = None
    input_label: str | None = None
    input_type: str = "number"
    input_min: int | None = None
    input_max: int | None = None


class TableWidgetMap(BaseModel):
    kind: str = "table"
    key: str
    title: str
    columns: list[TableColumnMap]
    rows: list[dict[str, object]]
    row_href_key: str | None = None  # if set, rows become clickable links using this key's value as href
    action_url: str | None = None
    id_key: str | None = None
    actions: list[TableActionMap] = Field(default_factory=list)


class ListWidgetMap(BaseModel):
    kind: str = "list"
    key: str
    title: str
    items: list[str] = Field(default_factory=list)


class ConfigEntryRow(BaseModel):
    key: str
    current: str
    default: str
    value_type: str
    is_modified: bool = False
    label: str | None = None
    description: str | None = None
    choices: list[dict[str, str]] = Field(default_factory=list)


class EditableConfigWidget(DashboardWidget):
    kind: str = "editable_config"


class EditableConfigWidgetMap(BaseModel):
    kind: str = "editable_config"
    key: str
    title: str
    namespace: str
    redirect_to: str
    update_url: str
    reset_url: str
    reset_namespace_url: str | None = None
    entries: list[ConfigEntryRow] = Field(default_factory=list)
    span: int = 2


class ChartWidget(DashboardWidget):
    kind: str = "chart"
    chart_type: str = "bar"  # "bar" | "pie" | "doughnut" | "line"


class ChartWidgetMap(BaseModel):
    kind: str = "chart"
    key: str
    title: str
    chart_type: str  # "bar" | "pie" | "doughnut" | "line"
    labels: list[str]
    datasets: list[dict[str, Any]]  # Chart.js dataset format
    height: int = 280  # px
    options: dict[str, Any] = Field(default_factory=dict)  # extra Chart.js options merged on top of defaults
    span: int = 1  # grid column span: 1 = normal, 2 = full-width

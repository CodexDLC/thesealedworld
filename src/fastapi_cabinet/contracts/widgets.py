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


class TableWidgetMap(BaseModel):
    kind: str = "table"
    key: str
    title: str
    columns: list[TableColumnMap]
    rows: list[dict[str, object]]
    row_href_key: str | None = None  # if set, rows become clickable links using this key's value as href


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
    entries: list[ConfigEntryRow] = Field(default_factory=list)

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


class ListWidgetMap(BaseModel):
    kind: str = "list"
    key: str
    title: str
    items: list[str] = Field(default_factory=list)

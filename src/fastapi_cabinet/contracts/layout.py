from pydantic import BaseModel, Field

from fastapi_cabinet.contracts.navigation import HeaderItem, SidebarItem


class CabinetLayoutMap(BaseModel):
    mount_path: str
    title: str
    active_module: str | None
    header: list[HeaderItem]
    sidebar: list[SidebarItem]
    sidebar_badges: dict[str, int | str] = Field(default_factory=dict)

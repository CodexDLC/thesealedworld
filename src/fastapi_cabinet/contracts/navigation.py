from pydantic import BaseModel


class SidebarItem(BaseModel):
    key: str
    label: str
    path: str
    icon: str = ""
    badge_key: str | None = None
    order: int = 100
    permission: str | None = None


class HeaderItem(BaseModel):
    key: str
    label: str
    path: str
    icon: str = ""
    group: str = "main"
    order: int = 100

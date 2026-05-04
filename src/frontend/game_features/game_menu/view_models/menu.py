from pydantic import BaseModel


class GameMenuItemVM(BaseModel):
    id: str
    label: str
    url: str
    icon: str | None = None
    panel: str | None = None
    panel_view: str | None = None
    window: str | None = None
    is_active: bool = False
    is_disabled: bool = False


class GameMenuVM(BaseModel):
    """
    View Model for the 5-slot game header menu.
    Slots: l2, l1, center, r1, r2
    """

    l2: GameMenuItemVM | None = None
    l1: GameMenuItemVM | None = None
    center: GameMenuItemVM | None = None
    r1: GameMenuItemVM | None = None
    r2: GameMenuItemVM | None = None

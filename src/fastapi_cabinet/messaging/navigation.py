from __future__ import annotations

from fastapi_cabinet.contracts.navigation import SidebarItem


def build_messaging_sidebar(
    *,
    inbox_path: str,
    mailing_path: str,
    registrations_path: str,
    unread_badge_key: str = "unread",
    pending_badge_key: str = "pending",
) -> tuple[SidebarItem, ...]:
    return (
        SidebarItem(key="inbox", label="Входящие", path=inbox_path, badge_key=unread_badge_key, order=10),
        SidebarItem(key="mailing", label="Рассылки", path=mailing_path, order=20),
        SidebarItem(
            key="registrations", label="Заявления", path=registrations_path, badge_key=pending_badge_key, order=30
        ),
    )


__all__ = ["build_messaging_sidebar"]

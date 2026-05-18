from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from starlette.responses import RedirectResponse, Response

from fastapi_cabinet.contracts.admin import CabinetAdmin
from fastapi_cabinet.contracts.navigation import SidebarItem
from fastapi_cabinet.contracts.widgets import TableWidget
from fastapi_cabinet.feedback.presenter import FeedbackCabinetPresenter

if TYPE_CHECKING:
    from fastapi import Request

    from fastapi_cabinet.feedback.bridge import FeedbackBridge


class FeedbackAdmin(CabinetAdmin):
    key = "feedback"
    label = "Фидбек"
    icon = ""
    group = "messaging"
    group_label = "Сообщения"
    path = "/admin/feedback"
    order = 40

    bridge: ClassVar[FeedbackBridge]

    sidebar = (
        SidebarItem(key="all", label="Все", path="/admin/feedback", order=10),
        SidebarItem(key="bugs", label="Баги", path="/admin/feedback/bugs", badge_key="bugs", order=20),
        SidebarItem(key="wishes", label="Пожелания", path="/admin/feedback/wishes", order=30),
        SidebarItem(key="impressions", label="Впечатления", path="/admin/feedback/impressions", order=40),
        SidebarItem(key="balance", label="Баланс", path="/admin/feedback/balance", order=50),
    )

    dashboard_widgets = (
        TableWidget(key="feedback_list", title="Фидбек", provider="feedback.list", order=10),
    )
    providers: ClassVar[dict] = {}
    sub_pages: ClassVar[dict] = {
        "bugs": (),
        "wishes": (),
        "impressions": (),
        "balance": (),
    }
    action_routes: ClassVar[dict] = {"action": ("POST", "handle_feedback_action")}

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        bridge = getattr(cls, "bridge", None)
        if bridge is None:
            return
        presenter = FeedbackCabinetPresenter()

        async def _feedback_provider(request: Request):
            state = await bridge.get_feedback_list_state(request=request)
            return presenter.feedback_widget(state)

        cls.providers = {**getattr(cls, "providers", {}), "feedback.list": _feedback_provider}

    async def get_sidebar_badges(self, request: Request) -> dict[str, int | str]:
        bridge = getattr(self.__class__, "bridge", None)
        if bridge is None:
            return {}
        state = await bridge.get_feedback_list_state(request=request, type_filter="bug")
        return {"bugs": state.new_count}

    async def handle_feedback_action(self, request: Request) -> Response:
        bridge = getattr(self.__class__, "bridge", None)
        if bridge is None:
            return RedirectResponse(url="/admin/feedback", status_code=303)
        form = await request.form()
        feedback_id = str(form.get("feedback_id", ""))
        new_status = str(form.get("status", ""))
        await bridge.update_feedback_status(request=request, feedback_id=feedback_id, status=new_status)
        return RedirectResponse(url="/admin/feedback", status_code=303)


__all__ = ["FeedbackAdmin"]

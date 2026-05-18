from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from starlette.responses import RedirectResponse, Response

from fastapi_cabinet.contracts.admin import CabinetAdmin
from fastapi_cabinet.contracts.navigation import SidebarItem
from fastapi_cabinet.contracts.widgets import TableWidget
from fastapi_cabinet.messaging.navigation import build_messaging_sidebar
from fastapi_cabinet.messaging.presenter import MessagingCabinetPresenter
from fastapi_cabinet.messaging.workflows import MessagingWorkflowService

if TYPE_CHECKING:
    from fastapi import Request

    from fastapi_cabinet.messaging.bridge import MessagingBridge


class InboxAdmin(CabinetAdmin):
    key = "inbox"
    label = "Входящие"
    icon = ""
    group = "messaging"
    group_label = "Сообщения"
    path = "/admin/inbox"
    order = 10

    bridge: ClassVar[MessagingBridge]

    sidebar = build_messaging_sidebar(
        inbox_path="/admin/inbox",
        mailing_path="/admin/mailing",
        registrations_path="/admin/registrations",
    )
    dashboard_widgets = (
        TableWidget(key="inbox_list", title="Входящие сообщения", provider="messaging.inbox", order=10),
    )
    providers: ClassVar[dict] = {}

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        bridge = getattr(cls, "bridge", None)
        if bridge is None:
            return
        presenter = MessagingCabinetPresenter()

        async def _inbox_provider(request: Request):  # type: ignore[return]
            state = await bridge.get_inbox_state(request=request)
            return presenter.inbox_widget(state)

        cls.providers = {**getattr(cls, "providers", {}), "messaging.inbox": _inbox_provider}

    async def get_sidebar_badges(self, request: Request) -> dict[str, int | str]:
        bridge = getattr(self.__class__, "bridge", None)
        if bridge is None:
            return {}
        state = await bridge.get_inbox_state(request=request)
        return {"unread": state.unread_count}


class MassMailingAdmin(CabinetAdmin):
    key = "mailing"
    label = "Рассылки"
    icon = ""
    group = "messaging"
    group_label = "Сообщения"
    path = "/admin/mailing"
    order = 20

    bridge: ClassVar[MessagingBridge]

    sidebar = (
        SidebarItem(key="overview", label="Все рассылки", path="/admin/mailing", order=10),
        SidebarItem(key="new", label="Новая рассылка", path="/admin/mailing/new", order=20),
    )
    dashboard_widgets = (TableWidget(key="mailing_list", title="Рассылки", provider="messaging.mailing", order=10),)
    providers: ClassVar[dict] = {}
    sub_pages: ClassVar[dict] = {"new": ()}

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        bridge = getattr(cls, "bridge", None)
        if bridge is None:
            return
        presenter = MessagingCabinetPresenter()

        async def _mailing_provider(request: Request):  # type: ignore[return]
            state = await bridge.get_mailing_list_state(request=request)
            return presenter.mailing_widget(state)

        cls.providers = {**getattr(cls, "providers", {}), "messaging.mailing": _mailing_provider}


class RegistrationAdmin(CabinetAdmin):
    key = "registrations"
    label = "Заявления"
    icon = ""
    group = "messaging"
    group_label = "Сообщения"
    path = "/admin/registrations"
    order = 30

    bridge: ClassVar[MessagingBridge]

    sidebar = (
        SidebarItem(key="pending", label="Ожидают", path="/admin/registrations", badge_key="pending", order=10),
        SidebarItem(key="reviewed", label="Рассмотренные", path="/admin/registrations/reviewed", order=20),
    )
    dashboard_widgets = (
        TableWidget(
            key="registration_list", title="Заявки на регистрацию", provider="messaging.registrations", order=10
        ),
    )
    providers: ClassVar[dict] = {}
    sub_pages: ClassVar[dict] = {"reviewed": ()}
    action_routes: ClassVar[dict] = {"action": ("POST", "handle_registration_action")}

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        bridge = getattr(cls, "bridge", None)
        if bridge is None:
            return
        presenter = MessagingCabinetPresenter()

        async def _registrations_provider(request: Request):  # type: ignore[return]
            state = await bridge.get_registration_list_state(request=request)
            return presenter.registration_widget(state)

        cls.providers = {**getattr(cls, "providers", {}), "messaging.registrations": _registrations_provider}

    async def get_sidebar_badges(self, request: Request) -> dict[str, int | str]:
        bridge = getattr(self.__class__, "bridge", None)
        if bridge is None:
            return {}
        state = await bridge.get_registration_list_state(request=request)
        return {"pending": state.pending_count}

    async def handle_registration_action(self, request: Request) -> Response:
        bridge = getattr(self.__class__, "bridge", None)
        if bridge is None:
            return RedirectResponse(url="/admin/registrations", status_code=303)
        form = await request.form()
        request_id = str(form.get("request_id", ""))
        action = str(form.get("action", ""))
        workflow = MessagingWorkflowService(bridge=bridge)
        await workflow.handle_registration_action(request=request, request_id=request_id, action=action)
        return RedirectResponse(url="/admin/registrations", status_code=303)


__all__ = ["InboxAdmin", "MassMailingAdmin", "RegistrationAdmin"]

from fastapi_cabinet import cabinet_site
from fastapi_cabinet.messaging import InboxAdmin, MassMailingAdmin, RegistrationAdmin
from src.frontend.features.cabinet.modules.messaging.bridge import SiteMessagingBridge
from src.frontend.features.email.config import get_email_service

_bridge = SiteMessagingBridge(email_service=get_email_service())


class SiteInboxAdmin(InboxAdmin):
    bridge = _bridge


class SiteMassMailingAdmin(MassMailingAdmin):
    bridge = _bridge


class SiteRegistrationAdmin(RegistrationAdmin):
    bridge = _bridge


cabinet_site.register(SiteInboxAdmin)
cabinet_site.register(SiteMassMailingAdmin)
cabinet_site.register(SiteRegistrationAdmin)

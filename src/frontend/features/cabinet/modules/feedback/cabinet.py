from fastapi_cabinet import cabinet_site
from fastapi_cabinet.feedback import FeedbackAdmin
from src.frontend.features.cabinet.modules.feedback.bridge import SiteFeedbackBridge

_bridge = SiteFeedbackBridge()


class SiteFeedbackAdmin(FeedbackAdmin):
    bridge = _bridge


cabinet_site.register(SiteFeedbackAdmin)

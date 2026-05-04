from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.site_features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService
from src.shared.utils.dev_utils import log_debug_payload

router = APIRouter(tags=["Cabinet"])


@router.get("/cabinet", name="cabinet")
async def cabinet_page(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
):
    user = await auth_service.require_current_user(request)
    log_debug_payload("cabinet_page.cabinet_page", user, enabled=settings.debug)
    return await ui.render("site/cabinet/index.html", context={"user": user})

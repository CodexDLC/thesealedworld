from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService

router = APIRouter(tags=["Cabinet"])


@router.get("/admin", name="cabinet")
async def cabinet_page(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
):
    user = await auth_service.require_current_user(request)
    return await ui.render("site/cabinet/index.html", context={"user": user})

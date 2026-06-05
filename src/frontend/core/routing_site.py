from collections.abc import Sequence

from fastapi import APIRouter

from src.frontend.config.settings import settings
from src.frontend.features.account.routes.email_verify import router as account_email_verify_router
from src.frontend.features.account.routes.pages import router as account_router
from src.frontend.features.auth.api import router as auth_api_router
from src.frontend.features.auth.routes.pages import router as auth_router
from src.frontend.features.feedback.routes.pages import router as feedback_router
from src.frontend.features.library.routes.pages import router as library_router
from src.frontend.features.news.routes.pages import router as news_router
from src.frontend.features.public_site.routes.pages import router as frontend_pages_router
from src.frontend.features.surveys.routes.pages import router as surveys_router

_SITE_ROUTERS: list[APIRouter] = [
    frontend_pages_router,
    news_router,
    library_router,
    auth_api_router,
    auth_router,
    account_router,
    feedback_router,
    surveys_router,
]

if settings.enable_email_verification:
    _SITE_ROUTERS.append(account_email_verify_router)

SITE_ROUTERS: Sequence[APIRouter] = tuple(_SITE_ROUTERS)

from datetime import timedelta
from typing import Any, cast

from authx import AuthXConfig

from src.frontend.config.settings import FrontendSettings


def build_authx_config(settings: FrontendSettings) -> AuthXConfig:
    return AuthXConfig(
        JWT_SECRET_KEY=settings.secret_key,
        JWT_ALGORITHM=cast("Any", settings.authx_jwt_algorithm),
        JWT_TOKEN_LOCATION=cast("Any", settings.authx_jwt_token_locations),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=settings.access_token_expire_minutes),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=settings.refresh_token_expire_days),
    )

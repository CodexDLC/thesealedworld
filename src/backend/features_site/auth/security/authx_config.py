from datetime import timedelta

from authx import AuthXConfig

from src.backend.config.settings import BackendSettings


def build_authx_config(settings: BackendSettings) -> AuthXConfig:
    return AuthXConfig(
        JWT_SECRET_KEY=settings.secret_key,
        JWT_ALGORITHM=settings.authx_jwt_algorithm,
        JWT_TOKEN_LOCATION=settings.authx_jwt_token_locations,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=settings.access_token_expire_minutes),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=settings.refresh_token_expire_days),
    )

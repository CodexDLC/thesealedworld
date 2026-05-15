from authx import AuthX

from src.frontend.config.settings import settings
from src.frontend.features.auth.security.authx_config import build_authx_config

authx: AuthX = AuthX(config=build_authx_config(settings))

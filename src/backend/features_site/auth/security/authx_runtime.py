from authx import AuthX

from src.backend.config.settings import settings
from src.backend.features_site.auth.security.authx_config import build_authx_config

authx: AuthX = AuthX(config=build_authx_config(settings))

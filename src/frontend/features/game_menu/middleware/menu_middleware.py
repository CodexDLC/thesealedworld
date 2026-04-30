from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.frontend.features.game_menu.services.menu_service import GameMenuService


class GameMenuMiddleware(BaseHTTPMiddleware):
    """
    Injects the GameMenuService into the request state.
    This allows the UIRenderer or other services to easily build
    the dynamic header menu.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Attach the service to request state
        request.state.game_menu_service = GameMenuService()

        response = await call_next(request)
        return response

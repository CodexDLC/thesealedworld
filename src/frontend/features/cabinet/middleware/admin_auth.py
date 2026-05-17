from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

_ADMIN_PREFIX = "/admin"


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Blocks /admin and /admin/* for non-superusers.

    Must run after AuthUserMiddleware (i.e. be registered before it in app.py).
    - Not logged in → redirect to /login
    - Logged in but not superuser → redirect to /
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path == _ADMIN_PREFIX or path.startswith(f"{_ADMIN_PREFIX}/"):
            user = getattr(request.state, "user", None)
            if user is None:
                return RedirectResponse(url="/login", status_code=303)
            if not user.is_superuser:
                return RedirectResponse(url="/", status_code=303)
        return await call_next(request)

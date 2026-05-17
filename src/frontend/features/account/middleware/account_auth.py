from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

_ACCOUNT_PREFIX = "/account"


class AccountAuthMiddleware(BaseHTTPMiddleware):
    """Blocks /account and /account/* for unauthenticated users.

    Must run after AuthUserMiddleware (i.e. be registered before it in app.py).
    - Not logged in → redirect to /login
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path == _ACCOUNT_PREFIX or path.startswith(f"{_ACCOUNT_PREFIX}/"):
            user = getattr(request.state, "user", None)
            if user is None:
                return RedirectResponse(url="/login", status_code=303)
        return await call_next(request)

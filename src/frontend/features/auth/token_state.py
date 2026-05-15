from fastapi import HTTPException, Request, status

ACCESS_COOKIE_NAME = "tbmmorpg_access_token"
REFRESH_COOKIE_NAME = "tbmmorpg_refresh_token"


def get_access_token(request: Request) -> str | None:
    state = getattr(request, "state", None)
    return getattr(state, "access_token", None) or request.cookies.get(ACCESS_COOKIE_NAME)


def require_access_token(request: Request) -> str:
    token = get_access_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return token

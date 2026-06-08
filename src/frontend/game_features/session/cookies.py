from fastapi import HTTPException, Request, Response, status

from src.frontend.config.settings import settings

ACTIVE_CHARACTER_COOKIE = "tbmmorpg_active_character_id"


def set_active_character_cookie(response: Response, character_id: int) -> None:
    response.set_cookie(
        ACTIVE_CHARACTER_COOKIE,
        str(character_id),
        httponly=True,
        samesite="lax",
        path="/",
        secure=settings.active_character_cookie_secure,
    )


def clear_active_character_cookie(response: Response) -> None:
    domain = settings.auth_cookie_domain or None
    response.delete_cookie(ACTIVE_CHARACTER_COOKIE, path="/", domain=domain)
    if domain:
        # Also expire any legacy host-only cookie left from before the
        # domain-scoped scheme, so a stale duplicate cannot survive the clear.
        response.delete_cookie(ACTIVE_CHARACTER_COOKIE, path="/")


def active_character_id_from_cookie(request: Request) -> int:
    raw_value = request.cookies.get(ACTIVE_CHARACTER_COOKIE)
    if raw_value is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/game-lobby"})
    try:
        character_id = int(raw_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/game-lobby"}) from exc
    if character_id <= 0:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/game-lobby"})
    return character_id

from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["Play Entry"])


@router.get("/", name="play_root")
async def play_root() -> RedirectResponse:
    return RedirectResponse("/game-lobby", status_code=status.HTTP_303_SEE_OTHER)

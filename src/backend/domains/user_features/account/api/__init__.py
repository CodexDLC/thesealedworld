from fastapi import APIRouter

from src.backend.domains.user_features.account.api import router as login_router
from src.backend.domains.user_features.account.api.lobby import router as lobby_router
from src.backend.domains.user_features.account.api.onboarding import router as onboarding_router
from src.backend.domains.user_features.account.api.registration import router as registration_router

router = APIRouter()

# Собираем роутеры с префиксами
# Итоговые пути будут: /account/register, /account/lobby/..., /account/onboarding/..., /account/login/
# (при условии, что этот router подключен с prefix="/account")

router.include_router(registration_router)  # Внутри уже есть /register
router.include_router(lobby_router, prefix="/lobby")
router.include_router(onboarding_router, prefix="/onboarding")
router.include_router(login_router, prefix="/login")

from fastapi import APIRouter, Depends

from src.backend.domains.user_features.account.gateway.registration_gateway import RegistrationGateway
from src.shared.schemas.response import CoreResponseDTO
from src.shared.schemas.user import UserDTO, UserUpsertDTO

router = APIRouter(tags=["Account Registration"])


@router.post("/register", response_model=CoreResponseDTO[UserDTO])
async def register_user(user_dto: UserUpsertDTO, gateway: RegistrationGateway = Depends()):
    """
    Регистрация или обновление пользователя.
    """
    return await gateway.upsert_user(
        telegram_id=user_dto.telegram_id,
        username=user_dto.username,
        first_name=user_dto.first_name,
        last_name=user_dto.last_name,
        language_code=user_dto.language_code,
        is_premium=user_dto.is_premium,
    )

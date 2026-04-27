import time
from typing import cast

from src.backend.database.redis.manager.account_manager import AccountManager
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.account_context import (
    AccountContextDTO,
    AttributesDict,
    BioDict,
    LocationDict,
    MetricsDict,
    SessionsDict,
    StatsDict,
)
from src.shared.schemas.character import CharacterReadDTO
from src.shared.schemas.errors import SessionExpiredError


class AccountSessionService:
    """
    Высокоуровневый сервис сессий (Lobby, Onboarding, Login).
    Обертка над AccountManager.
    Отвечает за:
    1. Сборку AccountContextDTO из CharacterReadDTO.
    2. Валидацию данных (DTO <-> Dict).
    3. Управление кэшем лобби (через AccountManager).
    """

    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager

    # --- Session Management (ac:{char_id}) ---

    async def create_session(self, character: CharacterReadDTO, initial_state: CoreDomain) -> AccountContextDTO:
        """
        Создает новую сессию (ac:{char_id}) на основе данных персонажа.
        """
        # 1. Сборка контекста
        context = self._build_context(character, initial_state)

        # 2. Сохранение в Redis
        await self.account_manager.create_account(character.character_id, context.model_dump())

        return context

    async def get_session(self, char_id: int) -> AccountContextDTO:
        """
        Получает сессию персонажа.
        """
        data = await self.account_manager.get_full_account(char_id)
        if not data:
            raise SessionExpiredError(f"Session expired for char_id {char_id}")

        try:
            return AccountContextDTO.model_validate(data)
        except Exception:  # noqa: BLE001
            # Если данные битые, считаем сессию невалидной
            raise SessionExpiredError(f"Invalid session data for char_id {char_id}") from None

    async def update_bio(self, char_id: int, bio: BioDict) -> None:
        """
        Обновляет секцию bio.
        """
        await self.account_manager.update_bio(char_id, cast(dict, bio))

    async def update_state(self, char_id: int, state: CoreDomain) -> None:
        """
        Обновляет стейт.
        """
        await self.account_manager.set_state(char_id, state)

    async def update_stats(self, char_id: int, stats: StatsDict) -> None:
        """
        Обновляет статы в сессии.
        """
        # Добавляем last_update, если его нет
        if "last_update" not in stats:
            stats["last_update"] = time.time()

        await self.account_manager.update_account_fields(char_id, {"stats": stats})

    async def get_state(self, char_id: int) -> str:
        state = await self.account_manager.get_state(char_id)
        if not state:
            raise SessionExpiredError(f"Session expired for char_id {char_id}")
        return state

    # --- Lobby Cache ---

    async def get_lobby_cache(self, user_id: int) -> list[CharacterReadDTO] | None:
        """
        Получает список персонажей из кэша лобби.
        """
        chars_data = await self.account_manager.get_lobby_cache(user_id)
        if chars_data is None:
            return None

        try:
            return [CharacterReadDTO.model_validate(char) for char in chars_data]
        except Exception:  # noqa: BLE001
            return None

    async def set_lobby_cache(self, user_id: int, characters: list[CharacterReadDTO]) -> None:
        """
        Сохраняет список персонажей в кэш лобби.
        """
        chars_data = [char.model_dump(mode="json") for char in characters]
        await self.account_manager.set_lobby_cache(user_id, chars_data)

    async def delete_lobby_cache(self, user_id: int) -> None:
        """
        Удаляет кэш лобби.
        """
        await self.account_manager.delete_lobby_cache(user_id)

    # --- Private Helpers ---

    def _build_context(self, character: CharacterReadDTO, state: CoreDomain) -> AccountContextDTO:
        """
        Собирает AccountContextDTO из CharacterReadDTO.
        """
        # Vitals
        hp_cur = character.vitals_snapshot.get("hp", {}).get("cur", 100) if character.vitals_snapshot else 100
        hp_max = character.vitals_snapshot.get("hp", {}).get("max", 100) if character.vitals_snapshot else 100

        mp_cur = character.vitals_snapshot.get("mp", {}).get("cur", 50) if character.vitals_snapshot else 50
        mp_max = character.vitals_snapshot.get("mp", {}).get("max", 50) if character.vitals_snapshot else 50

        # Attributes
        attributes = AttributesDict(
            strength=8, agility=8, endurance=8, intelligence=8, wisdom=8, men=8, perception=8, charisma=8, luck=8
        )

        return AccountContextDTO(
            state=state,
            bio=BioDict(
                name=character.name,
                gender=character.gender,
                created_at=character.created_at.isoformat() if character.created_at else None,
            ),
            location=LocationDict(current=character.location_id, prev=character.prev_location_id),
            stats=StatsDict(
                hp={"cur": hp_cur, "max": hp_max, "regen": 1.0},
                mp={"cur": mp_cur, "max": mp_max, "regen": 1.0},
                stamina={"cur": 100, "max": 100, "regen": 5.0},
                last_update=time.time(),
            ),
            attributes=attributes,
            sessions=SessionsDict(
                combat_id=character.active_sessions.get("combat_id") if character.active_sessions else None,
                inventory_id=character.active_sessions.get("inventory_id") if character.active_sessions else None,
                scenario_id=character.active_sessions.get("scenario_id") if character.active_sessions else None,
            ),
            metrics=MetricsDict(gear_score=0),
            skills={},
        )

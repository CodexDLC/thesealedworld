import time

from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher
from src.backend.domains.user_features.account.services.account_session_service import AccountSessionService
from src.backend.domains.user_features.arena.data.arena_resources import ArenaResources
from src.backend.domains.user_features.arena.services.arena_session_service import ArenaSessionService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.arena import ArenaScreenEnum, ArenaUIPayloadDTO

MATCHMAKING_TIMEOUT = 45


class ArenaService:
    def __init__(
        self, session_service: ArenaSessionService, dispatcher: SystemDispatcher, account_service: AccountSessionService
    ):
        self.session = session_service
        self.dispatcher = dispatcher
        self.account_service = account_service

    # --- Menu Methods ---

    async def get_main_menu(self) -> ArenaUIPayloadDTO:
        """Возвращает главное меню арены."""
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MAIN_MENU,
            title=ArenaResources.MAIN_TITLE,
            description=ArenaResources.MAIN_DESCRIPTION,
            buttons=ArenaResources.get_main_buttons(),
        )

    async def get_mode_menu(self, mode: str) -> ArenaUIPayloadDTO:
        """Возвращает меню выбранного режима."""
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MODE_MENU,
            mode=mode,
            title=ArenaResources.get_mode_title(mode),
            description=ArenaResources.get_mode_description(mode),
            buttons=ArenaResources.get_mode_buttons(mode),
        )

    # --- Queue Methods ---

    async def join_queue(self, char_id: int, mode: str) -> ArenaUIPayloadDTO:
        """
        Ставит игрока в очередь.
        """
        gs = await self.session.join_queue(char_id, mode)

        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.SEARCHING,
            mode=mode,
            title=ArenaResources.SEARCHING_TITLE,
            description=ArenaResources.SEARCHING_DESCRIPTION,
            gs=gs,
            buttons=ArenaResources.get_searching_buttons(mode),
        )

    async def check_match(self, char_id: int, mode: str) -> ArenaUIPayloadDTO | str:
        """
        Проверяет статус матча.
        Returns:
            ArenaUIPayloadDTO — если ещё ищем
            str "combat" — если матч найден (редирект)
        """
        request = await self.session.get_request_meta(char_id)
        if not request:
            return await self.get_main_menu()

        # 1. Поиск противника
        opponent_id = await self.session.find_opponent(char_id, mode)

        if opponent_id:
            # Матч найден — создаём PvP бой
            await self._create_battle(char_id, opponent_id, mode, battle_type="pvp")
            return "combat"

        # 2. Проверка таймаута
        start_time = float(request.get("start_time", 0))
        wait_time = time.time() - start_time

        if wait_time > MATCHMAKING_TIMEOUT:
            # Таймаут — создаём бой с Тенью
            await self._create_battle(char_id, None, mode, battle_type="shadow")
            return "combat"

        # 3. Продолжаем ждать
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.SEARCHING,
            mode=mode,
            title=ArenaResources.SEARCHING_TITLE,
            description=ArenaResources.SEARCHING_DESCRIPTION,
            gs=int(request.get("gs", 0)),
            buttons=ArenaResources.get_searching_buttons(mode),
        )

    async def cancel_queue(self, char_id: int, mode: str) -> ArenaUIPayloadDTO:
        """Отменяет поиск, возвращает меню режима."""
        await self.session.leave_queue(char_id, mode)
        return await self.get_mode_menu(mode)

    # --- Private Methods ---

    async def _create_battle(self, char_id: int, opponent_id: int | None, mode: str, battle_type: str) -> None:
        """
        Создаёт бой через SystemDispatcher.
        """
        # Очищаем данные сессии
        await self.session.prepare_match(char_id, opponent_id, mode)

        if battle_type == "shadow":
            # Бой с тенью
            await self.dispatcher.route(
                domain=CoreDomain.COMBAT_ENTRY, char_id=char_id, action="shadow_duel", context={"char_id": char_id}
            )
        else:
            # PvP бой
            teams = {"team_1": [char_id], "team_2": [opponent_id] if opponent_id else []}
            await self.dispatcher.route(
                domain=CoreDomain.COMBAT_ENTRY, char_id=char_id, action="arena_match", context={"teams": teams}
            )

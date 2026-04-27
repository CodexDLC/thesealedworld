from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.domains.user_features.game_menu.data.locales.menu_resources import MenuResources
from src.backend.services.utils.regen import calculate_regen
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.account_context import AccountContextDTO
from src.shared.schemas.errors import SessionExpiredError
from src.shared.schemas.game_menu import HUDDataDTO


class MenuSessionService:
    """
    Сервис для работы с сессией игрока в контексте меню.
    Отвечает за чтение данных из Redis, регенерацию и валидацию.
    """

    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager

    async def get_player_context(self, char_id: int) -> HUDDataDTO:
        """
        Получает актуальный контекст игрока (HUD) с учетом регенерации.

        Raises:
            SessionExpiredError: Если данные в Redis отсутствуют.
        """
        # 1. Получаем сырые данные из Redis
        raw_data = await self.account_manager.get_full_account(char_id)

        if not raw_data:
            raise SessionExpiredError(f"Session expired for char_id {char_id}")

        # Валидируем через DTO
        account_data = AccountContextDTO.model_validate(raw_data)

        # 2. Lazy Regen (Ленивая регенерация)
        stats_dict = account_data.stats

        regen_result = calculate_regen(stats_dict)

        if regen_result["is_changed"]:
            # 3. Если были изменения, сохраняем обратно в Redis
            await self.account_manager.update_account_fields(char_id, {"stats": regen_result["stats"]})
            account_data.stats = regen_result["stats"]

        # 4. Формируем HUD DTO
        stats = account_data.stats

        # Получаем красивое имя стейта
        state_name = MenuResources.get_state_name(account_data.state)

        return HUDDataDTO(
            hp=stats["hp"]["cur"],
            max_hp=stats["hp"]["max"],
            energy=stats["mp"]["cur"],
            max_energy=stats["mp"]["max"],
            char_name=account_data.bio["name"] or "Unknown",
            location_id=account_data.location["current"],
            current_mode=state_name,  # Теперь здесь "Exploration", а не "exploration"
        )

    async def get_current_state(self, char_id: int) -> str:
        state = await self.account_manager.get_state(char_id)
        if not state:
            raise SessionExpiredError(f"Session expired for char_id {char_id}")
        return state

    async def can_perform_action(self, char_id: int, target_action: str) -> bool:
        try:
            current_state = await self.get_current_state(char_id)
        except SessionExpiredError:
            return False

        allowed_states = {CoreDomain.EXPLORATION, CoreDomain.INVENTORY, CoreDomain.STATUS}

        return current_state in allowed_states

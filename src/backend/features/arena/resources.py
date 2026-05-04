from src.shared.schemas.arena import ArenaActionEnum, ArenaButtonDTO, ArenaModeEnum


class ArenaResources:
    MAIN_TITLE = "Ангар Арены"
    MAIN_DESCRIPTION = (
        "Испытательный полигон принимает заявки носителей. "
        "Здесь арена ищет противника, сверяет боевую сигнатуру и готовит переход к схватке."
    )

    SEARCHING_TITLE = "Поиск противника"
    SEARCHING_DESCRIPTION = "Сканирование сигнатур. Арена ищет соперника в допустимом диапазоне силы."

    PVP_PENDING_TITLE = "Противник найден"
    PVP_PENDING_DESCRIPTION = "Сигнатура подтверждена. Подтвердите переход на арену боя."

    SHADOW_PENDING_TITLE = "Активирована Тень"
    SHADOW_PENDING_DESCRIPTION = (
        "Живой противник не найден. Полигон поднимает симуляцию вашего боевого отражения."
    )
    SHADOW_OFFER_TITLE = "Тень готова"
    SHADOW_OFFER_DESCRIPTION = (
        "Живой противник не найден. Симуляция вашей боевой тени уже подготовлена; "
        "можно продолжить поиск или войти в бой."
    )

    COMBAT_FAILED_TITLE = "Вход в бой сорвался"
    COMBAT_FAILED_DESCRIPTION = "Противник найден, но сессия боя не была готова вовремя."

    _MODE_TITLES = {
        ArenaModeEnum.ONE_VS_ONE.value: "Схватка [1x1]",
        ArenaModeEnum.GROUP.value: "Командные бои",
        ArenaModeEnum.TOURNAMENT.value: "Турниры",
    }

    _MODE_DESCRIPTIONS = {
        ArenaModeEnum.ONE_VS_ONE.value: (
            "Классический бой один на один. Арена подберет противника по текущей боевой оценке."
        ),
        ArenaModeEnum.GROUP.value: "Командные бои будут доступны после переноса групповых комнат ожидания.",
        ArenaModeEnum.TOURNAMENT.value: "Турнирная сетка будет доступна позже.",
    }

    @staticmethod
    def get_main_buttons() -> list[ArenaButtonDTO]:
        return [
            ArenaButtonDTO(text="Схватка 1x1", action=ArenaActionEnum.MENU_MODE, mode=ArenaModeEnum.ONE_VS_ONE),
            ArenaButtonDTO(text="Командные бои", action=ArenaActionEnum.MENU_MODE, mode=ArenaModeEnum.GROUP),
            ArenaButtonDTO(text="Выйти", action=ArenaActionEnum.LEAVE, variant="ghost"),
        ]

    @staticmethod
    def get_mode_title(mode: str) -> str:
        return ArenaResources._MODE_TITLES.get(mode, "Неизвестный режим")

    @staticmethod
    def get_mode_description(mode: str) -> str:
        return ArenaResources._MODE_DESCRIPTIONS.get(mode, "Описание отсутствует.")

    @staticmethod
    def get_mode_buttons(mode: str) -> list[ArenaButtonDTO]:
        if mode == ArenaModeEnum.ONE_VS_ONE.value:
            return [
                ArenaButtonDTO(text="Найти противника", action=ArenaActionEnum.JOIN_QUEUE, mode=mode),
                ArenaButtonDTO(text="Назад", action=ArenaActionEnum.MENU_MAIN, variant="ghost"),
            ]
        return [ArenaButtonDTO(text="Назад", action=ArenaActionEnum.MENU_MAIN, variant="ghost")]

    @staticmethod
    def get_searching_buttons(mode: str) -> list[ArenaButtonDTO]:
        return [
            ArenaButtonDTO(text="Проверить", action=ArenaActionEnum.CHECK_MATCH, mode=mode),
            ArenaButtonDTO(text="Отмена", action=ArenaActionEnum.CANCEL_QUEUE, mode=mode, variant="ghost"),
        ]

    @staticmethod
    def get_pending_buttons(mode: str, arena_session_id: str) -> list[ArenaButtonDTO]:
        return [
            ArenaButtonDTO(
                text="Войти",
                action=ArenaActionEnum.CHECK_COMBAT_READY,
                mode=mode,
                value={"arena_session_id": arena_session_id},
            )
        ]

    @staticmethod
    def get_shadow_offer_buttons(mode: str, arena_session_id: str) -> list[ArenaButtonDTO]:
        return [
            ArenaButtonDTO(
                text="В бой с тенью",
                action=ArenaActionEnum.ACCEPT_SHADOW,
                mode=mode,
                value={"arena_session_id": arena_session_id},
            ),
            ArenaButtonDTO(
                text="Продолжить поиск",
                action=ArenaActionEnum.CONTINUE_SEARCH,
                mode=mode,
                value={"arena_session_id": arena_session_id},
                variant="ghost",
            ),
        ]

    @staticmethod
    def get_failed_buttons() -> list[ArenaButtonDTO]:
        return [ArenaButtonDTO(text="Вернуться на арену", action=ArenaActionEnum.MENU_MAIN)]

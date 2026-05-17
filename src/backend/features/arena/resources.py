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

    SHADOW_PENDING_TITLE = "Арена готова"
    SHADOW_PENDING_DESCRIPTION = "Тень материализована и готова вступить в бой."
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
        ArenaModeEnum.GROUP.value: (
            "Командный зал принимает ранговые заявки, свободные сборы и хаотические потасовки. "
            "Боевые комнаты пока работают в режиме проектного макета."
        ),
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
                ArenaButtonDTO(
                    text="Искать противника",
                    action=ArenaActionEnum.JOIN_QUEUE,
                    mode=mode,
                ),
                ArenaButtonDTO(text="Бой с тенью", action=ArenaActionEnum.START_SHADOW, mode=mode, variant="ghost"),
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
                value={"arena_session_id": arena_session_id, "confirm": True},
            ),
            ArenaButtonDTO(
                text="Отмена",
                action=ArenaActionEnum.CANCEL_QUEUE,
                mode=mode,
                value={"arena_session_id": arena_session_id},
                variant="ghost",
            ),
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

    @staticmethod
    def get_group_lobby_mock() -> dict:
        return {
            "primary_actions": [
                {
                    "id": "ranked",
                    "title": "Ранговый бой",
                    "kicker": "TEAM RANK",
                    "description": "Будущий выбор формата 3x3, 5x5 или 10x10 с отдельным командным рейтингом.",
                    "action": "group_ranked",
                    "meta": "3x3 / 5x5 / 10x10",
                },
                {
                    "id": "custom_request",
                    "title": "Создать заявку",
                    "kicker": "FREE REQUEST",
                    "description": "Неранговый сбор с форматом, таймером ожидания и комментарием для других игроков.",
                    "action": "group_custom_request",
                    "meta": "таймер + комментарий",
                },
                {
                    "id": "chaos",
                    "title": "Потасовка",
                    "kicker": "CHAOS",
                    "description": "Объявление на общий сбор с последующим авторазделением команд по рейтингу или gear score.",
                    "action": "group_chaos",
                    "meta": "авторазделение",
                },
            ],
            "tabs": [
                {
                    "id": "current",
                    "title": "Текущие бои",
                    "label": "LIVE",
                    "empty": "NO_DATA",
                    "items": [
                        {
                            "id": "mock-live-5x5",
                            "name": "Мостовые ворота",
                            "meta": "5x5 · идет 02:15 · рейтинг 1180",
                            "comment": "Тестовый бой для будущего наблюдения и вмешательства.",
                            "actions": [
                                {"text": "Смотреть", "action": "group_watch"},
                                {"text": "Вмешаться", "action": "group_intervene"},
                            ],
                        }
                    ],
                },
                {
                    "id": "chaos",
                    "title": "Хаотические бои",
                    "label": "CHAOS",
                    "empty": "NO_DATA",
                    "items": [
                        {
                            "id": "mock-chaos-queue",
                            "name": "Потасовка у нижних шлюзов",
                            "meta": "сбор 4 мин · 8 игроков · авто команды",
                            "comment": "После таймера арена сама разделит участников по силе.",
                            "actions": [
                                {"text": "Заявка", "action": "group_chaos_details"},
                                {"text": "Войти", "action": "group_chaos_join"},
                            ],
                        }
                    ],
                },
                {
                    "id": "requests",
                    "title": "Групповые заявки",
                    "label": "REQUESTS",
                    "empty": "NO_DATA",
                    "items": [
                        {
                            "id": "mock-request-3x3",
                            "name": "Заявка: Стражи Ржавого Круга",
                            "meta": "3x3 · таймер 6 мин · можно выбрать сторону",
                            "comment": "Нужны бойцы ближней линии, комментарий автора будет виден здесь.",
                            "actions": [
                                {"text": "Присоединиться", "action": "group_request_join"},
                                {"text": "Выбрать команду", "action": "group_pick_team"},
                            ],
                        }
                    ],
                },
            ],
        }

    @staticmethod
    def get_group_action_mock(action: str, item_id: str | None = None) -> dict:
        labels = {
            "group_ranked": "Ранговый бой",
            "group_custom_request": "Создать заявку",
            "group_chaos": "Потасовка",
            "group_watch": "Просмотр боя",
            "group_intervene": "Вмешательство",
            "group_chaos_details": "Заявка на потасовку",
            "group_chaos_join": "Вход в потасовку",
            "group_request_join": "Присоединение к заявке",
            "group_pick_team": "Выбор команды",
        }
        return {
            "action": action,
            "item_id": item_id,
            "title": labels.get(action, "Групповой режим"),
            "message": "Эта часть групповой арены пока работает на моковых данных и готовится к backend-логике.",
            "formats": ["3x3", "5x5", "10x10"],
            "status": "in_development",
        }

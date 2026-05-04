from src.shared.schemas.arena import ArenaActionEnum, ArenaModeEnum, ButtonDTO


class ArenaResources:
    # --- Constants ---
    MAIN_TITLE = "Ангар Арены"
    MAIN_DESCRIPTION = (
        "<b>Симбиот:</b> Добро пожаловать на испытательный полигон.\n"
        "Здесь вы можете проверить свои боевые навыки против других носителей "
        "или симуляций Тени.\n\n"
        "Выберите режим боя:"
    )

    SEARCHING_TITLE = "Поиск противника"
    SEARCHING_DESCRIPTION = (
        "<b>Симбиот:</b> Сканирование сигнатур...\n<i>Поиск подходящего соперника по GearScore...</i>\n\n{ANIMATION}"
    )

    # --- Mode Texts ---
    _MODE_TITLES = {
        ArenaModeEnum.ONE_VS_ONE.value: "Схватка [1x1]",
        ArenaModeEnum.GROUP.value: "Командные бои",
        ArenaModeEnum.TOURNAMENT.value: "Турниры",
    }

    _MODE_DESCRIPTIONS = {
        ArenaModeEnum.ONE_VS_ONE.value: (
            "<b>Режим: Дуэль</b>\n\n"
            "Классический бой один на один. Победитель получает рейтинг и ресурсы.\n"
            "Проигравший теряет прочность экипировки.\n\n"
            "<i>Готовы начать поиск?</i>"
        ),
        ArenaModeEnum.GROUP.value: "<b>Режим: Командный бой</b>\n\n🚧 Находится в разработке.",
        ArenaModeEnum.TOURNAMENT.value: "<b>Режим: Турнир</b>\n\n🚧 Находится в разработке.",
    }

    # --- Methods ---

    @staticmethod
    def get_main_buttons() -> list[ButtonDTO]:
        return [
            ButtonDTO(
                text="⚔️ Схватка (1x1)", action=ArenaActionEnum.MENU_MODE.value, mode=ArenaModeEnum.ONE_VS_ONE.value
            ),
            ButtonDTO(text="👥 Командные бои", action=ArenaActionEnum.MENU_MODE.value, mode=ArenaModeEnum.GROUP.value),
            ButtonDTO(text="🚪 Выйти с Полигона", action=ArenaActionEnum.LEAVE.value),
        ]

    @staticmethod
    def get_mode_title(mode: str) -> str:
        return ArenaResources._MODE_TITLES.get(mode, "Неизвестный режим")

    @staticmethod
    def get_mode_description(mode: str) -> str:
        return ArenaResources._MODE_DESCRIPTIONS.get(mode, "Описание отсутствует.")

    @staticmethod
    def get_mode_buttons(mode: str) -> list[ButtonDTO]:
        if mode == ArenaModeEnum.ONE_VS_ONE.value:
            return [
                ButtonDTO(
                    text="⚔️ Найти противника",
                    action=ArenaActionEnum.JOIN_QUEUE.value,
                    mode=ArenaModeEnum.ONE_VS_ONE.value,
                ),
                ButtonDTO(text="🔙 Назад", action=ArenaActionEnum.MENU_MAIN.value),
            ]
        else:
            # Для WIP режимов только кнопка назад
            return [ButtonDTO(text="🔙 Назад", action=ArenaActionEnum.MENU_MAIN.value)]

    @staticmethod
    def get_searching_buttons(mode: str) -> list[ButtonDTO]:
        return [ButtonDTO(text="❌ Отмена", action=ArenaActionEnum.CANCEL_QUEUE.value, mode=mode)]

    @staticmethod
    def get_match_found_text(opponent_name: str, is_shadow: bool) -> str:
        if is_shadow:
            return "<b>Симбиот:</b> Живой противник не найден.\n<i>Активация протокола 'Тень'...</i>"
        return f"<b>Симбиот:</b> Сигнатура подтверждена.\nПротивник: <b>{opponent_name}</b>"

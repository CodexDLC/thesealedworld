# src/backend/features/exploration/runtime/navigation.py
"""
Engine для сборки навигационной сетки.
Чистая логика без обращений к БД/Redis.
"""

from typing import Any

from src.shared.schemas.exploration import GridButtonDTO, NavigationGridDTO


class NavigationEngine:
    """
    Собирает NavigationGridDTO из данных локации.
    Stateless — все данные передаются в методы.
    
    Legacy: Сетка 3x3 для совместимости с интерфейсом Telegram-бота.
    В будущем будет переработано под веб-интерфейс.
    """

    # Маппинг направлений на смещения координат
    DIRECTION_OFFSETS: dict[str, tuple[int, int]] = {
        "n": (0, -1),  # Север: y уменьшается
        "s": (0, 1),  # Юг: y увеличивается
        "w": (-1, 0),  # Запад: x уменьшается
        "e": (1, 0),  # Восток: x увеличивается
    }

    DIRECTION_LABELS: dict[str, str] = {
        "n": "⬆️ СЕВЕР",
        "s": "⬇️ ЮГ",
        "w": "⬅️ ЗАПАД",
        "e": "➡️ ВОСТОК",
    }

    @classmethod
    def build_grid(
        cls,
        current_loc_id: str,
        exits: dict[str, Any],
        flags: dict[str, Any],
    ) -> NavigationGridDTO:
        """
        Собирает полную сетку навигации.

        Args:
            current_loc_id: ID текущей локации (формат "X_Y")
            exits: Словарь выходов из локации
            flags: Флаги локации (is_safe_zone, threat_tier, etc.)

        Returns:
            NavigationGridDTO с заполненными кнопками.
        """
        # Парсим текущие координаты
        cx, cy = cls._parse_coords(current_loc_id)

        # Если координаты не распарсились, используем 0,0 как dummy
        if cx is None or cy is None:
            cx, cy = 0, 0

        # Собираем кнопки направлений
        direction_buttons = cls._build_direction_buttons(cx, cy, exits)

        # Собираем контекстные кнопки (углы)
        context_buttons = cls._build_context_buttons(flags)

        # Собираем кнопки сервисов
        service_buttons = cls._build_service_buttons(exits)

        return NavigationGridDTO(
            # Крестовина
            n=direction_buttons.get("n", cls._make_wall_button("n")),
            s=direction_buttons.get("s", cls._make_wall_button("s")),
            w=direction_buttons.get("w", cls._make_wall_button("w")),
            e=direction_buttons.get("e", cls._make_wall_button("e")),
            # Углы
            nw=context_buttons["nw"],
            ne=context_buttons["ne"],
            sw=context_buttons["sw"],
            se=context_buttons["se"],
            # Центр
            center=cls._make_center_button(),
            # Сервисы
            services=service_buttons,
        )

    # =========================================================================
    # Direction Buttons (Крестовина)
    # =========================================================================

    @classmethod
    def _build_direction_buttons(cls, cx: int, cy: int, exits: dict[str, Any]) -> dict[str, GridButtonDTO]:
        """
        Строит кнопки направлений на основе exits.
        """
        buttons: dict[str, GridButtonDTO] = {}

        for key, data in exits.items():
            if not isinstance(data, dict):
                continue

            # Парсим ключ (может быть "nav:52_51" или просто "52_51")
            prefix, target_id = cls._parse_exit_key(key)

            if prefix != "nav":
                continue  # Сервисы обрабатываются отдельно

            # Определяем направление по координатам
            direction = cls._get_direction_from_target(cx, cy, target_id)
            if not direction:
                continue

            # Извлекаем время перехода
            travel_time = float(data.get("time_duration", 0.0))

            buttons[direction] = GridButtonDTO(
                id=direction,
                label=cls.DIRECTION_LABELS[direction],
                action=f"move:{target_id}:{travel_time}",
                is_active=True,
                style="primary",
            )

        return buttons

    @classmethod
    def _get_direction_from_target(cls, cx: int, cy: int, target_id: str) -> str | None:
        """
        Определяет направление по целевым координатам.
        """
        tx, ty = cls._parse_coords(target_id)
        if tx is None or ty is None:
            return None

        dx, dy = tx - cx, ty - cy

        for direction, (expected_dx, expected_dy) in cls.DIRECTION_OFFSETS.items():
            if dx == expected_dx and dy == expected_dy:
                return direction

        return None

    # =========================================================================
    # Context Buttons (Углы)
    # =========================================================================

    @classmethod
    def _build_context_buttons(cls, flags: dict[str, Any]) -> dict[str, GridButtonDTO]:
        """
        Строит контекстные кнопки (углы сетки).
        """
        is_safe = flags.get("is_safe_zone", False)

        return {
            # NW: Поиск
            "nw": GridButtonDTO(
                id="search",
                label="🔍 ПОИСК",
                action="interact:search",
                is_active=True,
                style="secondary",
            ),
            # NE: Режим боя/мир
            "ne": GridButtonDTO(
                id="combat_mode",
                label="☮️ МИР" if is_safe else "⚔️ БОИ",
                action="interact:safe_zone" if is_safe else "interact:battles",
                is_active=True,
                style="secondary",
            ),
            # SW: Люди
            "sw": GridButtonDTO(
                id="people",
                label="👥 ЛЮДИ",
                action="interact:people",
                is_active=True,
                style="secondary",
            ),
            # SE: Авто-навигация
            "se": GridButtonDTO(
                id="auto",
                label="🧭 АВТО",
                action="interact:navigator",
                is_active=True,
                style="secondary",
            ),
        }

    # =========================================================================
    # Service Buttons (Нижний ряд)
    # =========================================================================

    @classmethod
    def _build_service_buttons(cls, exits: dict[str, Any]) -> list[GridButtonDTO]:
        """
        Строит кнопки сервисов (входы в здания).
        """
        services: list[GridButtonDTO] = []

        for key, data in exits.items():
            if not isinstance(data, dict):
                continue

            prefix, target_id = cls._parse_exit_key(key)

            if prefix != "svc":
                continue

            button_text = data.get("text_button", "Вход")

            services.append(
                GridButtonDTO(
                    id=f"svc_{target_id}",
                    label=f"🚪 {button_text}",
                    action=f"service:{target_id}",
                    is_active=True,
                    style="primary",
                )
            )

        return services

    # =========================================================================
    # Center Button
    # =========================================================================

    @classmethod
    def _make_center_button(cls) -> GridButtonDTO:
        """
        Кнопка центра — обзор/обновление.
        """
        return GridButtonDTO(
            id="look",
            label="👁 ОБЗОР",
            action="interact:look_around",
            is_active=True,
            style="secondary",
        )

    # =========================================================================
    # Wall Button (неактивное направление)
    # =========================================================================

    @classmethod
    def _make_wall_button(cls, direction: str) -> GridButtonDTO:
        """
        Кнопка-заглушка для заблокированного направления.
        """
        return GridButtonDTO(
            id=direction,
            label="⛔️",
            action="blocked",
            is_active=False,
            style="secondary",
        )

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _parse_coords(loc_id: str) -> tuple[int | None, int | None]:
        """
        Парсит координаты из ID локации (формат "X_Y").
        """
        try:
            parts = loc_id.split("_")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        except ValueError:
            pass
        return None, None

    @staticmethod
    def _parse_exit_key(key: str) -> tuple[str, str]:
        """
        Парсит ключ выхода.
        "nav:52_51" -> ("nav", "52_51")
        "svc:tavern" -> ("svc", "tavern")
        "52_51" -> ("nav", "52_51")
        """
        if ":" in key:
            parts = key.split(":", 1)
            return parts[0], parts[1]
        return "nav", key

class MenuResources:
    """
    Статические ресурсы для Game Menu.
    Тексты кнопок и конфигурации лейаутов.
    """

    # Button IDs
    BTN_ID_INVENTORY = "inventory"
    BTN_ID_STATUS = "status"
    BTN_ID_EXPLORATION = "exploration"

    # Button Labels (Icons only)
    LABELS = {BTN_ID_INVENTORY: "📦", BTN_ID_STATUS: "ℹ️", BTN_ID_EXPLORATION: "🗺️"}

    # Descriptions for HUD Legend (Русский)
    DESCRIPTIONS = {BTN_ID_INVENTORY: "Инвентарь", BTN_ID_STATUS: "Статус", BTN_ID_EXPLORATION: "Навигация"}

    # State Names (Human Readable - Русский, Нейтральный)
    # Отображается в HUD игрока: "Режим: Исследование"
    STATE_NAMES = {
        "exploration": "Исследование",
        "inventory": "Инвентарь",
        "status": "Статус",
        "combats": "Бой",
        "scenario": "Сценарий",
        "lobby": "Лобби",
        "arena": "Арена",
        "onboarding": "Создание персонажа",
    }

    # Layouts
    DEFAULT_LAYOUT = [BTN_ID_STATUS, BTN_ID_INVENTORY, BTN_ID_EXPLORATION]

    @classmethod
    def get_label(cls, btn_id: str) -> str:
        return cls.LABELS.get(btn_id, "?")

    @classmethod
    def get_description(cls, btn_id: str) -> str:
        return cls.DESCRIPTIONS.get(btn_id, btn_id)

    @classmethod
    def get_layout(cls) -> list[str]:
        return cls.DEFAULT_LAYOUT

    @classmethod
    def get_state_name(cls, state: str) -> str:
        """Возвращает читаемое название стейта."""
        return cls.STATE_NAMES.get(state, state.capitalize())

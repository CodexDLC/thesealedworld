# колбэки хранят структуры данных для обработки нажатий кнопок
from aiogram.filters.callback_data import CallbackData


class SystemCallback(CallbackData, prefix="sys"):
    """
    Base callback data for system commands.
    Used for basic navigation if needed.
    """

    action: str
    target: str = "main"

from aiogram.filters.callback_data import CallbackData


class AnnouncementsCallback(CallbackData, prefix="announcements"):
    """Callback for background tasks interaction."""

    action: str
    task_id: str | None = None

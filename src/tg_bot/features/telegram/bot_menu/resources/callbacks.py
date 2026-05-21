from aiogram.filters.callback_data import CallbackData


class DashboardCallback(CallbackData, prefix="dashboard"):
    """
    Callback data for the dashboard.
    """

    action: str = "select"
    target: str = "main"

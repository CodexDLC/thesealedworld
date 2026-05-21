def get_dashboard_title(mode: str = "bot_menu") -> str:
    """Returns the title based on the current dashboard mode."""
    if mode == "dashboard_admin":
        return "🛠 <b>Admin Dashboard</b>"
    return "📱 <b>Main Menu</b>"

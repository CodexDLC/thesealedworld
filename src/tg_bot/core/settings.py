"""
Static configuration for the Telegram Bot 'tg_bot'.
Contains lists of features and other non-secret settings.
"""

from typing import Any

# --- Telegram Features (Aiogram Routers) ---
# List feature folder names from 'features/telegram/'
INSTALLED_FEATURES: list[str] = [
    "commands",
    "bot_menu",
    "community_feed",
]

# --- Background Features (Redis Stream Listeners) ---
# List feature folder names from 'features/redis/'
INSTALLED_REDIS_FEATURES: list[str] = [
    "announcements",
]


# --- Custom Middlewares ---
# Add your custom project middleware instances here.
# They will be automatically registered AFTER the core framework ones.
# Example: CUSTOM_MIDDLEWARES = [MyAnalyticsMiddleware(), LoggingMiddleware()]
CUSTOM_MIDDLEWARES: list[Any] = []


# --- System ---
# Mandatory core middlewares are managed automatically in core/factory.py
# You can add other static constants here

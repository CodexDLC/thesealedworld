# 🏛 Project Architecture: Tg_bot

This project is built using the `codex-bot` framework, which implements Enterprise-grade patterns for Telegram bot development.

## 🧱 Separation of Concerns

| Component | Location | Responsibility |
| :--- | :--- | :--- |
| **Library** | `codex-bot` | Core engine, DI container, Director, ViewSender, Middlewares. |
| **App Code** | `src/tg_bot/` | Bot settings, handlers, feature logic (orchestrators). |
| **Infrastructure**| `src/tg_bot/infrastructure/` | DB connections, Redis, External API clients. |

## 🎯 Key Concepts

### 1. Logic-less Handlers
In this architecture, files in `handlers/` contain zero business logic. They only intercept Telegram updates and delegate execution to the Orchestrator via the automatic `Director`.

### 2. Orchestrator Pattern (Feature Brain)
The Orchestrator acts as a bridge between data and the UI. It is stateless and unaware of the Telegram API. it operates with DTOs, requests data from services, and returns results to the UI layer.

### 3. Director Pattern (Navigation)
The Director manages transitions between "scenes" (features). To switch a user to another function, simply call `await director.set_scene("feature_name")`.

### 4. ViewSender Pattern (SPA in Telegram)
The bot behaves like a "Single Page Application". Instead of spamming new messages, the `ViewSender` edits existing interface blocks (Menu and Content), tracking their coordinates in Redis.

### 5. Auto-discovery
No need to register routers manually. Simply add your feature folder name to the `INSTALLED_FEATURES` list in `core/settings.py`.

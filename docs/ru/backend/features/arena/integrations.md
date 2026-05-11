# Integrations

## ArenaSessionIntegration

Фасад над `ArenaSessionStore` для работы с очередью и матчами. Используется в `ArenaService`.

Отвечает за: управление очередью (`join_queue`, `find_opponent`, `leave_queue`), runtime-сессии, матчи, match lock, gear score.

GS-балансировка: `GS_RANGE_PERCENT = 0.15` — оппонент ищется в диапазоне ±15% от gear score игрока.

::: backend.features.arena.integrations.session_integration.ArenaSessionIntegration
    options:
      show_source: false
      show_root_heading: false
      members: []

---

## ArenaSystemIntegrator

Связь арены с внешними доменами: создание commitment, запрос combat сессии, вход/выход персонажа.

::: backend.features.arena.integrations.arena_integration.ArenaIntegration
    options:
      show_source: false
      show_root_heading: false
      members: []

---

## ArenaStreamClient

Отправка событий арены в Event Bus (Redis Streams). Используется для асинхронных запросов к другим доменам (gear score, combat creation).

::: backend.features.arena.integrations.stream_client.ArenaStreamClient
    options:
      show_source: false
      show_root_heading: false

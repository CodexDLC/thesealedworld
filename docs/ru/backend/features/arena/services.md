# Services

## ArenaService

Главный сервис арены — управляет полным жизненным циклом игрока от входа до старта боя.

**Ключевые методы:**

| Метод | Действие |
|-------|---------|
| `enter_arena` | Создаёт/восстанавливает runtime сессию |
| `view` | Возвращает текущий экран с enriched рейтингом |
| `join_queue` | Создаёт commitment, ставит в очередь → SEARCHING |
| `check_match` | Ищет оппонента с distributed lock, создаёт матч |
| `check_combat_ready` | Проверяет готовность матча, подтверждает вход в бой |
| `start_shadow` | Запускает тренировку против копии персонажа |
| `accept_shadow` | Подтверждает shadow после SHADOW_OFFER |
| `continue_search` | Из SHADOW_OFFER обратно в pvp-поиск |
| `cancel_queue` | Выход из очереди → MODE_MENU |
| `leave` | Полный выход из арены, очистка всех Redis-данных |

**Match lock** — `check_match` берёт distributed lock перед поиском оппонента чтобы исключить race condition когда два игрока одновременно пытаются создать матч друг с другом.

::: backend.features.arena.services.arena_service.ArenaService
    options:
      show_source: false
      show_root_heading: false
      members: []

---

## RatingService

Расчёт и обновление рейтинга после боя.

::: backend.features.arena.services.rating_service.RatingService
    options:
      show_source: false
      show_root_heading: false

---

## RatingViewService

Чтение рейтинговых данных для отображения в UI.

::: backend.features.arena.services.rating_view_service.ArenaRatingViewService
    options:
      show_source: false
      show_root_heading: false

---

## SeasonService

Управление сезонами арены.

::: backend.features.arena.services.season_service.SeasonService
    options:
      show_source: false
      show_root_heading: false

---

## DuelService / GroupService

::: backend.features.arena.services.duel_service.DuelService
    options:
      show_source: false
      show_root_heading: false

::: backend.features.arena.services.group_service.GroupService
    options:
      show_source: false
      show_root_heading: false

# План покрытия тестами (Testing Coverage Plan)

Этот документ описывает стратегию увеличения покрытия тестами с текущих **15.02%** до требуемых **90.0%**. План разбит на этапы по приоритетности: от критической инфраструктуры до второстепенных компонентов.

## Состояние на текущий момент (Baseline)
- **Total Coverage:** 15.02%
- **Target:** 90.0%
- **Critical Gaps:** Backend `app.py`, Core Feature Logic (Scenario, World, ActorState), Frontend Core.

---

## Этап 1: Инфраструктура и Точки входа (Infrastructure & Entry Points)
**Приоритет:** Высокий (Mandatory)
**Цель:** Обеспечить стабильный запуск и работу базовых систем.

| Компонент | Текущее % | Цель % | Действие |
|-----------|-----------|--------|----------|
| `src/backend/app.py` | 0% | 100% | Тестирование инициализации FastAPI, подключения middleware и роутеров. |
| `src/backend/core/bus/router.py` | 54% | 100% | Полное покрытие логики маршрутизации сообщений. |
| `src/backend/core/database/session.py` | 76% | 100% | Тестирование жизненного цикла сессий и обработки ошибок БД. |
| `src/backend/core/redis/actor_snapshot_manager.py` | 74% | 100% | Покрытие пограничных случаев (missing keys, connection errors). |

---

## Этап 2: Аутентификация и Безопасность (Security & Auth)
**Приоритет:** Критический (Safety)
**Цель:** Гарантировать защиту данных и корректность авторизации.

| Компонент | Текущее % | Цель % | Действие |
|-----------|-----------|--------|----------|
| `src/backend/features/auth/services/auth_service.py` | 59% | 100% | Тестирование логики JWT, обновления токенов и смены паролей. |
| `src/backend/features/auth/repositories/` | 50-52% | 100% | CRUD операции с пользователями и токенами. |
| `src/backend/features/auth/dependencies.py` | 0% | 100% | Проверка извлечения данных пользователя из запроса. |
| `src/backend/features/auth/api/router.py` | 0% | 100% | Интеграционные тесты эндпоинтов `/login`, `/register`. |

---

## Этап 3: Основной игровой цикл - Backend (Core Game Loop)
**Приоритет:** Высокий (Core Logic)
**Цель:** Покрыть логику управления персонажами и миром.

| Модуль | Приоритетные файлы | Описание |
|--------|---------------------|----------|
| **Actor State** | `repositories/db/*`, `services/actor_state_service.py`, `runtime/assemblers/*` | Сохранение/загрузка состояния персонажей и монстров. |
| **Game Lobby** | `services/lobby_service.py`, `services/character_creation_service.py` | Создание лобби и генерация персонажей. |
| **World** | `services/navigation_service.py`, `repositories/world_repository.py` | Перемещение по локациям и кэширование карты. |

---

## Этап 4: Игровая механика и Сценарии (Narrative & Mechanics)
**Приоритет:** Средний (Complexity)
**Цель:** Тестирование движка квестов и боев.

| Модуль | Приоритетные файлы | Описание |
|--------|---------------------|----------|
| **Scenario** | `engine/director.py`, `engine/evaluator.py`, `services/scenario_service.py` | Логика прогресса квестов и условий выполнения. |
| **Combat** | `runtime/engine/*`, `workers/*` | Механика пошагового боя (навыки, урон, расчеты). |
| **Exploration** | `services/*`, `events/*` | Случайные события и исследование территорий. |

---

## Этап 5: Frontend Core и Интеграция (UI Reliability)
**Приоритет:** Средний (UX Safety)
**Цель:** Проверка связи фронтенда с бэкендом.

| Компонент | Описание |
|-----------|----------|
| `src/frontend/core/api.py` | Покрытие базового HTTP клиента. |
| `src/frontend/integrations/backend_api/*` | Типизированные вызовы к API бэкенда. |
| `src/frontend/features/auth/services/*` | Логика входа/регистрации на стороне клиента. |

---

## Этап 6: Схемы, Перечисления и DTO (Percentage Fill)
**Приоритет:** Низкий (Volume)
**Цель:** Добор процентов покрытия через проверку статических определений.

| Модуль | Описание |
|--------|----------|
| `src/shared/schemas/*` | Валидация Pydantic моделей (Character, Item, Skill). |
| `src/shared/enums/*` | Проверка корректности маппинга перечислений. |
| `src/backend/features/*/dto/*` | Маппинг данных между слоями. |

---

## График выполнения (Timeline Hypothesis)
1. **Infrastructure & Auth (Этапы 1-2):** +15% покрытия (~30% total)
2. **Actor State & Game Lobby (Этап 3):** +20% покрытия (~50% total)
3. **World & Scenario (Этап 4):** +25% покрытия (~75% total)
4. **Frontend & Shared (Этапы 5-6):** +15% покрытия (~90% total)

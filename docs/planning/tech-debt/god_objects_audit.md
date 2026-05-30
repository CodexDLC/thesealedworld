# God Objects Audit — Backend

> Аудит проведён 2025-05-19. Анализ всех `src/backend/features/` и `src/backend/infrastructure/`.
> `features_site/` — тонкие роутеры без логики, миграция на фронтенд завершена.

---

## Tier 1 — Критичные файлы (>500 строк, массивное смешение ответственностей)

### 1. ~~`CombatResolver` — 1,106 строк, 32 метода~~ ✅ DONE (refactor/combat-resolver-package)

**Файл:** `src/backend/features/combat/runtime/engine/resolver/` (был `resolver.py`)

Декомпозирован в пакет с императивным оркестратором, 7 простыми `ResolverStep`-классами,
суб-пайплайном `DamageStep` (7 фаз) и 5 support-модулями. Публичный контракт
(`CombatResolver.resolve_exchange`) сохранён бит-в-бит. `__init__.py` ужался до 55 строк.

**Раскладка пакета:**

```
src/backend/features/combat/runtime/engine/resolver/
├── __init__.py            — CombatResolver facade (resolve_exchange only)
├── orchestrator.py        — imperative run_exchange(...) with explicit early-returns
├── steps/
│   ├── _base.py           — ResolverStep (__slots__ = ())
│   ├── accuracy.py        — AccuracyStep + accuracy_step singleton
│   ├── crit.py            — CritStep
│   ├── evasion.py         — EvasionStep
│   ├── parry.py           — ParryStep
│   ├── block.py           — BlockStep
│   ├── counter_check.py   — CounterCheckStep
│   ├── healing.py         — HealingStep
│   └── damage/            — sub-pipeline (Phase 5 decomposition)
│       ├── damage_step.py — DamageStep + damage_step singleton
│       ├── _state.py      — DamageState dataclass(slots=True)
│       ├── raw_roll.py    — init + raw_damage
│       ├── physical.py    — physical mitigation + armor + crit
│       ├── pure.py        — pure damage
│       ├── elemental.py   — 8-element loop + heavy-armor subsequent penalty
│       ├── shield_absorb.py
│       ├── final_clamp.py — damage_mult + cap + res.damage_final
│       └── damage_event.py — trace + HIT event
└── support/
    ├── trace_writer.py     — trace_roll/trace_step/trace_damage + compact helpers
    ├── offensive_lookup.py — get_offensive_val, accuracy_skill_bonus
    ├── armor_math.py       — effective_armor*, effective_physical_resistance, calculate_crit_multiplier
    ├── token_awarder.py    — bonus_token_roll, award_token / attacker / defender
    └── trigger_activator.py — resolve_triggers, trigger_chance, apply_*_effects/token_grants
```

**Закреплено тестом:** `tests/backend/features/combat/runtime/engine/test_resolver_trigger_contract.py`
фиксирует множество эмитируемых триггер-событий (12 имён, `ON_DAMAGE` — dormant,
не эмитится по дизайну).

---

### 2. `CombatSessionManager` — 980 строк, 54+ методов

**Файл:** `src/backend/infrastructure/combat/managers/session.py`

9 типов Redis-ключей, Lua-скрипты (128+ строк в `universal_hot_join`), логи, аналитика, локи — всё в одном классе.

**Рекомендация:** Разбить на домены:
- `CombatRedisKeyFactory` — статические `*_key()` методы (9 шт)
- `CombatRedisScripts` — Lua-скрипты как отдельные единицы
- `CombatLogRepository` — append/get/group/slice логов
- `CombatAnalyticsRepository` — аналитика и маппинг
- `CombatLockManager` — acquire/release busy/worker локов
- `CombatSessionManager` — только lifecycle сессий (create, get_meta, set_winner, cleanup)

---

### 3. `LLMWorldGenerator` — 900+ строк, 28 методов

**Файл:** `src/backend/features/world/services/generator_service.py`

Генерация D4 столицы, нодов, навигации, AI-задач, координатной математики — всё внутри. Хардкод `D4_DISTRICT_PROFILES` на 80 строк.

**Рекомендация:**
- `D4NodeBuilder` — построение нодов (тип, гейты, стены, рифты)
- `D4MovementCalculator` — блокированные выходы, 8-направленный скан
- `D4ContentContextBuilder` — сбор тегов, районов, маршрутов
- `D4DistrictProfiles` — вынести профили в конфиг/константы
- `LLMWorldGenerator` — тонкий оркестратор

---

### 4. `ItemFactory` — 805 строк, 35+ методов

**Файл:** `src/backend/features/items/runtime/item_factory.py`

Генерация предметов + скейлинг + аффиксы + нейминг (с русской грамматикой) + материалы + бандлы + проекция.

**Рекомендация:**
- `AffixRoller` — выбор, бросок, бандл-логика (~15 методов)
- `ItemNameBuilder` — детерминированные имена/описания, согласование префиксов
- `ItemStatScaler` — power, durability, implicit bonus scaling
- `ItemFactory` — оркестратор: `generate_player_item()`, `generate_runtime_item()`

---

### 5. `ExpeditionService` — 775 строк, 36 методов, 6 зависимостей

**Файл:** `src/backend/features/expedition/service.py`

Lifecycle + инвентарь + ресурсы + прогрессия + смерть + SQL-запросы прямо в сервисе. Дублированная логика консолидации предметов/ресурсов.

**Рекомендация:**
- `ExpeditionLifecycleService` — create, start, end, respawn
- `ExpeditionInventoryService` — перемещение предметов (экспедиция ↔ персонаж ↔ труп)
- `ExpeditionProgressionService` — XP, скиллы
- `ExpeditionDeathService` — создание трупа, финализация, передача лута
- SQL-запросы — вынести в `ExpeditionRepository`

---

### 6. `ScenarioSystemIntegrator` — 768 строк, 40+ методов, 6+ зависимостей

**Файл:** `src/backend/features/scenario/integrations/system_integrator.py`

Сессии + контент-провайдер + награды (инвентарь, скиллы, атрибуты, виталы) + NPC + комбат + туториал.

**Рекомендация:**
- `ScenarioSessionManager` — Redis session CRUD + бэкапы
- `ScenarioContentProvider` — доступ к квестам/нодам (обёртка)
- `ScenarioRewardOrchestrator` — раздача предметов/скиллов/атрибутов
- `ScenarioSystemIntegrator` — тонкий фасад

---

### 7. `CombatSessionService` — 639 строк, 30+ методов

**Файл:** `src/backend/features/combat/services/session_service.py`

Session queries + move registration + result archival + log aggregation + winner inference.

**Рекомендация:**
- `CombatSessionResolver` — резолв session_id, finalization_id
- `CombatLogAggregator` — группировка, нарезка, подсчёт логов
- `CombatOutcomeCalculator` — определение победителя, outcome, summary
- `CombatResultBuilder` — построение архивных результатов
- `CombatSessionService` — регистрация ходов и dashboard

---

### 8. `ArenaDuelService` — 542 строки, 30 методов

**Файл:** `src/backend/features/arena/services/duel_service.py`

Очередь + матчмейкинг + shadow-бои + UI-пейлоады + локи. `check_match` — 100 строк вложенной логики.

**Рекомендация:**
- `DuelQueueService` — join/leave/continue очереди
- `DuelMatchService` — матчмейкинг и статус
- `DuelPayloadBuilder` — UI-пейлоады (pending, shadow_offer, failed)

---

### 9. `CombatExecutor` — 539 строк, 20+ методов

**Файл:** `src/backend/features/combat/runtime/processors/executor.py`

Обработка волн атак + периодические эффекты + логи + dead actor tracking.

**Рекомендация:**
- `ExchangeWaveProcessor` — управление волнами, pending очередь
- `PeriodicEffectProcessor` — тик периодических эффектов
- `CombatExecutor` — оркестратор обмена

---

## Tier 2 — Высокий риск (300–500 строк)

### 10. `ExplorationService` — 490 строк, 14 методов

**Файл:** `src/backend/features/exploration/services/exploration_service.py`

Движение + энкаунтеры + кеширование + навигация DTO + скиллы + угрозы.

**Рекомендация:**
- `ExplorationNavigationService` — move, location data, player tracking
- `ExplorationEncounterOrchestrator` — генерация и кеш энкаунтеров

---

### 11. `MonsterClanGenerationBuilder` — 419 строк, 15+ методов

**Файл:** `src/backend/features/monsters/runtime/generation_builder.py`

Выбор семьи + планирование членов + запросы экипировки + текст + визуал.

**Рекомендация:**
- `MonsterFamilySelector` — доступность и выбор семьи
- `MonsterMemberPlanner` — варианты, тиры
- `MonsterEquipmentRequestBuilder` — предметные запросы
- `MonsterFlavorBuilder` — текст и визуал

---

### 12. `ScenarioService` — 408 строк

**Файл:** `src/backend/features/scenario/services/scenario_service.py`

`finalize()` — 170 строк, 10+ последовательных async-вызовов, 10 типов событий.

**Рекомендация:**
- `ScenarioFinalizationOrchestrator` — награды, эффекты, переход в комбат
- `ScenarioService` — initialize, resume, step (роутинг запросов)

---

### 13. `GameLobbyIntegration` — 373 строки, 14 методов, 11 зависимостей

**Файл:** `src/backend/features/game_lobby/integrations/system_integrator.py`

Рекордсмен по coupling: 11 параметров в `__init__` (character_repo, attributes_repo, skill_repo, progression_repo, expedition_repo, inventory_repo, item_persistence, scenario_service, db_session, character_sessions, events).

**Рекомендация:**
- `CharacterScenarioOrchestrator` — setup/cleanup сценариев
- `CharacterDeletionService` — удаление с трансфером предметов
- Уменьшить `__init__` до 3–4 через композицию

---

### 14. `CityService` — 361 строка, 16 методов

**Файл:** `src/backend/features/city_services/services.py`

`_payload` — 187 строк с 11 ветками. Tavern/portal логика размазана по 4+ методам.

**Рекомендация:**
- `CityServiceScreenBuilder` — UI payload
- `TavernService` — tavern-специфичная логика (отдых, комнаты)
- `CityServiceButtonFactory` — генерация кнопок

---

### 15. `InventoryService` — 300+ строк, 20+ методов, 5 зависимостей

**Файл:** `src/backend/features/inventory/services/inventory_service.py`

Экипировка + пояс + прочность + gear score + сессии окна.

**Рекомендация:**
- `EquipmentSlotManager` — equip/unequip, валидация слотов, конфликты
- `BeltManager` — move_to_belt/remove, проверка ёмкости
- `DurabilityManager` — расчёт износа

---

## Tier 3 — Пограничные (200–300 строк, чрезмерный coupling)

| Класс | Файл | Строк | Deps | Главная проблема |
|-------|------|-------|------|------------------|
| `RatingService` | `arena/services/rating_service.py` | 283 | 4 | ELO + лиги + лидерборд + персистенция |
| `ExplorationEncounterService` | `exploration/services/encounter_service.py` | 271 | 5 | Роллы + bypass + сессии + XP в одном |
| `GameSessionIntegrator` | `game_session/integrations/session_integrator.py` | 261 | 7 | Пересекает 5 доменов; `Any`-типы в сигнатуре |
| `MonsterGroupService` | `monsters/services/monster_group_service.py` | 249 | 7 | 7 зависимостей, оркестрирует слишком много |
| `GenerationAIService` | `generation_ai/services.py` | 197 | 4 | Scheduling + execution + validation |

---

## Чистые фичи (без god-объектов)

- **loot** — хорошая архитектура: Engine → Service → Integration
- **npc** — 131 строк, 1 зависимость, 5 методов
- **moderation** — 70 строк, чистая валидация
- **system** — конфиг, нет бизнес-логики

---

## Системные антипаттерны

| Антипаттерн | Примеры | Встречается |
|-------------|---------|-------------|
| **Mega-метод (100+ строк)** | ~~CombatResolver._step_calculate_damage (215)~~ (resolved Phase 5), CityService._payload (187), ScenarioService.finalize (170) | 3+ раза |
| **Dependency hell (7+ deps)** | GameLobbyIntegration (11), GameSessionIntegrator (7), MonsterGroupService (7) | 3 класса |
| **SQL в сервисном слое** | ExpeditionService (select/delete/insert прямо в методах) | 1+ |
| **Embedded Lua** | CombatSessionManager (128+ строк Lua в Python-строках) | 1 |
| **Any-типы** | GameSessionIntegrator (expedition_service: Any, loot_arq: Any) | 1+ |
| **Фасад = дублирование** | ExplorationGateway, ArenaGateway — копируют логику сервисов | 2+ |

---

## Итого

| Tier | Кол-во | Описание |
|------|--------|----------|
| Критичные | 9 | >500 строк, множественные ответственности, тяжело тестировать |
| Высокий риск | 6 | 300–500 строк, нужен рефакторинг при следующем касании |
| Пограничные | 5 | 200–300 строк, чрезмерный coupling |
| Чистые фичи | 4 | Хорошая архитектура, образцы для подражания |

Самые токсичные для тестируемости: **CombatResolver** (монолитная математика), **CombatSessionManager** (Lua-скрипты), **ExpeditionService** (SQL + 6 зависимостей).

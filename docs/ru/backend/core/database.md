# Database

`src/backend/core/database/` — SQLAlchemy async engine, сессии, базовые модели.

## Base и TimestampMixin

`Base` — декларативная база всех ORM-моделей. Задаёт naming convention для constraints (индексы, FK, PK) — это важно для Alembic, который генерирует миграции по имени constraint.

`TimestampMixin` — добавляет `created_at` / `updated_at` через `server_default=func.now()`. Подключается к любой модели наследованием.

```python
class Character(Base, TimestampMixin):
    __tablename__ = "characters"
    ...
```

## Сессии

Два способа получить сессию:

| Способ | Когда использовать |
|--------|-------------------|
| `get_db()` | FastAPI dependency injection (`Depends(get_db)`) |
| `get_session_context()` | Вне HTTP-контекста — bootstrap, workers, скрипты |

`get_session_context()` делает `commit` при успехе и `rollback` при любом исключении.

## model_imports

`src/backend/core/database/model_imports.py` — единственный файл который импортирует все ORM-модели. Нужен только для того чтобы Alembic видел полный `Base.metadata` при генерации миграций. Больше нигде не используется напрямую.

Все модели зарегистрированные здесь:

`User`, `RefreshToken`, `Character`, `CharacterAttributes`, `CharacterSymbiote`, `SkillProgress`, `ItemInstance`, `ItemOrigin`, `ItemPlacement`, `ItemTransaction`, `ResourceBalance`, `ResourceTransaction`, `InventoryItem`, `ResourceWallet`, `GeneratedClanORM`, `GeneratedMonsterORM`, `ScenarioMaster`, `ScenarioNode`, `CharacterQuestState`, `WorldRegion`, `WorldZone`, `WorldGrid`, `ArenaBrawlXP`, `ArenaLeague`, `ArenaMatch`, `ArenaRating`, `ArenaSeason`, `ArenaSeasonReward`, `ArenaTeam`, `ArenaTeamMembership`, `CombatFinalization`

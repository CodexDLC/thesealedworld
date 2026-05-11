# Lifespan

`src/backend/core/lifespan.py` — FastAPI lifespan context manager. Определяет строгий порядок запуска и остановки всех контейнеров.

## Порядок старта

```mermaid
sequenceDiagram
    participant F as FastAPI
    participant L as lifespan()
    participant DB as DatabaseContainer
    participant RD as RedisContainer
    participant AI as AIContainer
    participant GF as GameFeatureContainer

    F->>L: startup
    L->>DB: bootstrap(app)
    Note over DB: Alembic migrations, SQLAlchemy engine
    L->>RD: bootstrap(app)
    Note over RD: Redis client, managers, stream runtimes, event bind
    L->>AI: bootstrap(app)
    Note over AI: Google Gemini client → app.state.ai
    L->>GF: bootstrap(app)
    Note over GF: World locations, scenario JSON load
    L-->>F: yield (сервер принимает запросы)
    F->>L: shutdown
    L->>L: stop stream runtimes
    L->>L: close arq, redis_client
```

## app.state после старта

После успешного старта на `app.state` доступны:

| Ключ | Тип | Устанавливает |
|------|-----|---------------|
| `redis_client` | `redis.asyncio.Redis` | RedisContainer |
| `redis` | `RedisService` | RedisContainer |
| `redis_managers` | `RedisManagers` | RedisContainer |
| `events` | `GameEventProducer` | RedisContainer |
| `stream_runtimes` | `list[StreamRuntime]` | RedisContainer |
| `game_config` | `GameConfigManager` | RedisContainer |
| `character_sessions` | manager | RedisContainer |
| `actor_commitments` | manager | RedisContainer |
| `ai` | AI client | AIContainer |
| `world_cache_loaded_count` | `int` | GameFeatureContainer |

`src/backend/core/lifespan.py` — `lifespan(app)` async context manager, передаётся в `FastAPI(lifespan=lifespan)`.

# Core

`src/backend/core/` — инфраструктурное ядро бекенда. Не содержит игровой логики — только фундамент на котором стоят все features.

```mermaid
flowchart TD
    L[lifespan.py] --> DB[DatabaseContainer]
    L --> RD[RedisContainer]
    L --> AI[AIContainer]
    L --> GF[GameFeatureContainer]
    RD --> BUS[GameEventProducer / Bus]
    RD --> MGR[Redis Managers]
    RD --> SR[Stream Runtimes]
    GF --> WB[World Bootstrap]
    GF --> SC[Scenario Bootstrap]
```

## Модули

| Модуль | Назначение |
|--------|-----------|
| `lifespan.py` | FastAPI lifespan — порядок старта/стопа всех контейнеров |
| `containers/` | Четыре контейнера: Database, Redis, AI, GameFeature |
| `bus/` | `GameEventProducer` — адаптер Event Bus (Redis Streams) |
| `calculators/` | Waterfall-калькулятор статов, шанс-сервис, прогрессия навыков |
| `database/` | SQLAlchemy сессия, base-модель, импорт всех моделей |
| `arq.py` | ARQ-воркер (фоновые задачи) |
| `ai.py` | Клиент AI (Google Gemini) |
| `schemas/` | Базовые Pydantic-схемы |
| `security.py` | JWT / AuthX |
| `middleware.py` | FastAPI middleware |
| `exceptions.py` | Базовые исключения |

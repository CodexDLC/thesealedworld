# ARQ

`src/backend/core/arq.py` — фоновые задачи на базе `arq` (Redis-очереди).

## Две очереди

| Константа | Имя очереди | Назначение |
|-----------|-------------|-----------|
| `COMBAT_ARQ_QUEUE` | `tbmmorpg:arq:combat` | Боевые задачи (ходы AI, chaos, executor...) |
| `SYSTEM_ARQ_QUEUE` | `tbmmorpg:arq:system` | Системные задачи (sync AC, persistence...) |

## ArqService

Тонкая обёртка над `PlatformArqService`. При создании принимает `queue_name` — по умолчанию `COMBAT_ARQ_QUEUE`.

```python
# Постановка задачи в очередь
await arq.enqueue_job("sync_active_session_task", {"char_id": char_id})
```

`app.state.combat_arq` — для боевых задач, инициализируется в `RedisContainer`.
`app.state.system_arq` — для системных, инициализируется лениво в `ActiveCharacterDirtySyncMiddleware`.

## BaseArqSettings

Базовые настройки воркеров: `max_jobs=20`, `job_timeout=60`, `keep_result=5`. Наследуется воркером каждой очереди.

`base_startup` / `base_shutdown` — хуки жизненного цикла воркера: инициализируют `ArqWorkerContainer` с доступом к БД и Redis внутри воркер-процесса.

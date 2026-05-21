# Logging Optimization & Observability Plan

## Context

Проект TurnBasedMMORPG (7 сервисов: backend, frontend, chat, 4 ARQ worker'а) использует Loguru через codex_core. Текущие проблемы:

- **~240 лог-вызовов**, 60% info-спам, только 1 `logger.bind()` во всём проекте
- **Нет structured logging** — key=value внутри строк сообщений, Loki не может парсить
- **ANSI color codes** в prod stdout → мусор в Grafana Cloud Loki
- **Healthcheck спам** — `GET /health` каждые 10 секунд забивает логи
- **Нет request_id / correlation_id** в контексте логов
- **Нет app-level Prometheus метрик** (только cAdvisor container-level)
- **Нет dev дашборда**

Alloy уже работает на сервере (systemd), отправляет docker stdout в Grafana Cloud Loki и cAdvisor метрики в Grafana Cloud Prometheus. Нужно состыковать формат логов приложения с пайплайном Alloy.

## Deliverables

1. `docs/logging-rules.md` — правила логирования (MD-документ)
2. `codex_core` v0.4.0 — JSON prod sink, contextvars, healthcheck filter
3. Middleware: request context + Prometheus метрики
4. Alloy config update на сервере
5. Dev Grafana + Prometheus стек
6. AI sweep task prompt — задание для прохода по кодовой базе
7. Agent skill — `turnbasedmmorpg-logging-quality`

---

## Phase 1: Logging Rules Document

**Create:** `docs/logging-rules.md`

### Log Levels

| Level | Когда | Prod stdout | Пример |
|-------|-------|-------------|--------|
| DEBUG | внутренние решения логики, flow tracing | нет | `ScenarioConditionEvaluated`, cache hit/miss |
| INFO | бизнес-событие на границе операции | да | `CombatSessionCreated`, `WorkerInit` |
| WARNING | recoverable anomaly | да | `AuthRefreshRejected`, `DirtySyncSkipped` |
| ERROR | операция не выполнена | да | DB write failed, external API 500 |
| CRITICAL | сервис не может работать | да | startup/shutdown failure |

### Structured Logging Pattern

```python
# Правильно: context в bind, message — короткое PascalCase имя события
logger.bind(combat_id=cid, actor_count=len(actors)).info("CombatLifecycleReady")

# Правильно: простой случай с 1 полем через placeholder
logger.info("RegistryLoaded variant_count={}", count)

# НЕПРАВИЛЬНО: f-string
logger.info(f"Combat lifecycle ready: combat_id={cid}")

# НЕПРАВИЛЬНО: все поля в строке
logger.info("Combat lifecycle ready: combat_id={} source={}", id, src)
```

### Context Fields (автоматические через contextvars)

| Поле | Источник | Всегда |
|------|----------|--------|
| `service` | setup_logging patcher | да |
| `request_id` | LogContextMiddleware / logged_task | да |
| `char_id` | middleware path params / task payload | когда есть |
| `session_id` | logger.bind в бизнес-коде | когда есть |
| `correlation_id` | event handler wrapper | для event bus |
| `combat_id` | logger.bind в combat domain | combat only |
| `task_name` | logged_task decorator | workers only |
| `duration_ms` | logger.bind для timed ops | когда есть |

### Dev vs Prod

| | Dev (DEBUG=True) | Prod (DEBUG=False) |
|--|-----------------|-------------------|
| Console | colorized human-readable | JSON (serialize=True) |
| File sinks | debug.log + errors.json | нет (docker stdout only) |
| Console level | DEBUG | INFO |
| Healthchecks | видны | filtered |
| Backtrace/diagnose | да | нет |

### Что НЕ логировать

- Healthcheck запросы
- Request/response bodies (PII)
- Токены, пароли, ключи
- Per-item циклы (только summary)
- Static file serving

### Naming Conventions

- Field names: `snake_case` (`char_id`, `combat_id`, `duration_ms`)
- Event names в message: `PascalCase` (`CombatSessionCreated`, `WorkerInit`)
- Duration: всегда `duration_ms` (float, миллисекунды)
- Counts: суффикс `_count` (`actor_count`, `variant_count`)
- IDs: суффикс `_id` (`char_id`, `combat_id`)

---

## Phase 2: codex_core Changes

**Repo:** `C:\install\projects\codex_tools\codex-core`
**Bump:** 0.3.0 → 0.4.0

### 2A. New: `src/codex_core/common/log_context.py`

Contextvars-based log context для propagation через async call stack:

```python
import contextvars
from typing import Any

_log_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("log_context", default={})

def set_log_context(**kwargs: Any) -> None:
    current = _log_context.get().copy()
    current.update(kwargs)
    _log_context.set(current)

def clear_log_context() -> None:
    _log_context.set({})

def get_log_context() -> dict[str, Any]:
    return _log_context.get().copy()
```

### 2B. Modify: `src/codex_core/common/loguru_setup.py`

Ключевые изменения в `setup_logging()`:

1. **Patcher** — inject `service` + contextvars fields в каждый record:
   ```python
   def context_patcher(record):
       record["extra"]["service"] = service_name
       record["extra"].update(get_log_context())
   logger.configure(patcher=context_patcher)
   ```

2. **Healthcheck filter**:
   ```python
   def healthcheck_filter(record):
       return not record["extra"].get("healthcheck", False)
   ```

3. **Prod branch** (when `settings.debug is False`):
   - Один sink: stdout с `serialize=True`, `colorize=False`, `filter=healthcheck_filter`
   - Без file sinks (docker stdout → Alloy → Loki)

4. **Dev branch** (when `settings.debug is True`):
   - Текущее поведение (colored console + debug.log + errors.json)
   - Добавить `filter=healthcheck_filter` на console sink

### 2C. Export из `__init__.py`

`set_log_context`, `clear_log_context`, `get_log_context`

### 2D. Version bump + publish

`pyproject.toml` version → 0.4.0, build & publish.

---

## Phase 3: TurnBasedMMORPG Integration

**Depends on:** Phase 2 (codex_core 0.4.0)

### 3A. `pyproject.toml` — bump codex-core dependency

`codex-core>=0.4.0`

### 3B. New: `src/shared/log_middleware.py`

Starlette middleware для HTTP-сервисов (backend, frontend, chat):

- Генерирует `request_id` (UUID4)
- `set_log_context(request_id=...)`
- Детектит `/health` → `set_log_context(healthcheck=True)`
- Извлекает `char_id` из path params если есть
- Ставит `X-Request-ID` response header
- `clear_log_context()` в finally

### 3C. New: `src/shared/log_task_wrapper.py`

Decorator `@logged_task` для ARQ worker tasks:

- Генерирует `request_id`
- Ставит `task_name` = function name
- Извлекает `char_id`, `combat_id`, `session_id`, `correlation_id` из payload
- `clear_log_context()` в finally

### 3D. Modify app entry points — add middleware

| File | Action |
|------|--------|
| `src/backend/app.py` | `app.add_middleware(LogContextMiddleware)` |
| `src/frontend/app.py` | `app.add_middleware(LogContextMiddleware)` |
| `src/backend/chat/app.py` | `app.add_middleware(LogContextMiddleware)` + `setup_logging()` |

---

## Phase 4: Prometheus Integration

**Parallel with Phase 3**

### 4A. `pyproject.toml` — add `prometheus-client>=0.25.0`

### 4B. New: `src/shared/metrics.py`

Shared metrics registry:

- `http_requests_total` (counter) — `[service, method, path_template, status]`
- `http_request_duration_seconds` (histogram) — `[service, method, path_template]`
- `http_requests_in_flight` (gauge) — `[service]`
- `event_published_total` (counter) — `[service, event_type]`
- `event_processed_total` (counter) — `[service, event_type, status]`
- `service_info` (info)

Buckets для HTTP: `[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]`

### 4C. New: `src/shared/metrics_middleware.py`

`PrometheusMiddleware(BaseHTTPMiddleware)` — собирает HTTP метрики, пропускает `/metrics` и `/health`.

### 4D. New: `src/shared/metrics_endpoint.py`

`/metrics` endpoint (FastAPI Router) — `generate_latest(REGISTRY)` → PlainTextResponse.

### 4E. Modify app entry points

| File | Action |
|------|--------|
| `src/backend/app.py` | middleware + router |
| `src/frontend/app.py` | middleware + router |
| `src/backend/chat/app.py` | middleware + router |

### 4F. Modify: `src/backend/core/bus/producer.py`

Increment `event_published_total` на каждый `publish()` / `request()`.

### Workers (отложено)

ARQ workers не имеют HTTP — метрики через push gateway или sidecar будут в будущей итерации. Пока worker timing будет через structured JSON logs в Loki.

---

## Phase 5: Alloy Config Update (server)

**Depends on:** Phase 2 + Phase 4 deployed to prod

### 5A. Create: `deploy/alloy/config.alloy.prod`

Reference config для сервера. Дополнения к существующему `/etc/alloy/config.alloy`:

**JSON log parsing pipeline:**
```alloy
loki.process "app_json_logs" {
  stage.json {
    expressions = {
      level      = "record.level.name",
      service    = "record.extra.service",
      request_id = "record.extra.request_id",
      msg        = "text",
    }
  }
  stage.labels {
    values = { level = "", service = "" }
  }
  stage.structured_metadata {
    values = { request_id = "" }
  }
  forward_to = [loki.write.grafana_cloud_loki.receiver]
}
```

**App metrics scraping:**
```alloy
prometheus.scrape "app_metrics" {
  targets = [
    {"__address__" = "tbmmorpg-backend:8001",  "service" = "backend"},
    {"__address__" = "tbmmorpg-frontend:8000", "service" = "frontend"},
    {"__address__" = "tbmmorpg-chat:8002",     "service" = "chat"},
  ]
  metrics_path    = "/metrics"
  scrape_interval = "15s"
  forward_to      = [prometheus.remote_write.metrics_service.receiver]
}
```

**Route app containers через JSON pipeline** — добавить relabel rule по container name prefix `tbmmorpg-`.

### 5B. Apply на сервере

SSH → update `/etc/alloy/config.alloy` → `systemctl reload alloy`

---

## Phase 6: Dev Infrastructure

### 6A. New: `deploy/docker-compose.observability.yml`

```yaml
services:
  prometheus:
    image: prom/prometheus:v2.53.0
    container_name: tbmmorpg-prometheus
    ports: ["9090:9090"]
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro

  grafana:
    image: grafana/grafana:11.0.0
    container_name: tbmmorpg-grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_AUTH_ANONYMOUS_ENABLED: "true"
    ports: ["3000:3000"]
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
```

### 6B. New: `deploy/prometheus/prometheus.yml`

Scrape configs для backend:8001, frontend:8000, chat:8002.

### 6C. New: `deploy/grafana/provisioning/datasources/prometheus.yml`

Auto-provision Prometheus datasource.

### 6D. New: `deploy/grafana/dashboards/`

Provisioned dashboards (JSON):
1. **Service Overview** — request rate, error rate, p50/p95/p99 latency
2. **Request Details** — per-endpoint breakdown
3. **Service Health** — in-flight, error %, uptime

### 6E. Usage

```bash
# Dev с observability:
docker compose -f docker-compose.yml -f docker-compose.observability.yml up
```

---

## Phase 7: Codebase Sweep (AI Task)

**Depends on:** Phase 3 (middleware must exist)

**Create:** `docs/planning/tasks/logging-sweep-task.md`

Промпт для AI-агента на проход по всем ~99 файлам с `from loguru import logger`:

### Rules

1. **f-strings → bind/placeholder** (11 occurrences в 6 файлах)
2. **key=value в строке → logger.bind()** для всех контекстных полей
3. **Re-level шумные логи:**
   - `logger.info("Frontend router registered...")` → оставить INFO (startup)
   - `logger.info` в `src/frontend/core/api.py` (every backend call) → DEBUG
   - `logger.info("Frontend game token refreshed")` → DEBUG
   - `logger.info("Lobby page view loaded")` → DEBUG
   - `CombatCreationTiming` intermediate steps → DEBUG, `step=total` → INFO
4. **Standardize messages** → PascalCase event names
5. **Pipe-separator pattern** (`"WorkerInit | stage=start worker_type=combat"`) → `logger.bind(stage="start", worker_type="combat").info("WorkerInit")`
6. **Remove emoji** из log messages (src/frontend/core/static.py)
7. **Add @logged_task** decorator на все ARQ tasks
8. **Add correlation_id propagation** в event handlers (10 files)

### Processing Order

1. `src/shared/` (new infrastructure)
2. `src/backend/core/` (bus/producer, middleware, arq)
3. `src/backend/features/*/events/` (10 event handler files)
4. `src/backend/features/*/workers/` (4 worker types)
5. `src/backend/features/*/services/` (business logic)
6. `src/backend/features/*/api/` (HTTP handlers)
7. `src/frontend/core/` (api client, middleware, static)
8. `src/frontend/features/` + `src/frontend/game_features/`

---

## Phase 8: Agent Skill

**Create:** `docs/agent-skills/turnbasedmmorpg-logging-quality/SKILL.md`

Skill для enforcement правил логирования на новый и изменяемый код:

- Trigger: когда review или пишется код с logger calls, или добавляется новый feature
- Checks: bind vs f-string, PascalCase events, correct log level, no PII, @logged_task on workers, correlation_id in event handlers
- References: `docs/logging-rules.md`
- Interaction: runs before `turnbasedmmorpg-quality-gate`

---

## Execution Order & Dependencies

```
Phase 1 (logging-rules.md)
   |
Phase 2 (codex_core 0.4.0)
   |
Phase 3 (middleware) --+-- Phase 4 (prometheus) [parallel]
                       |
                 Phase 5 (alloy config) <- requires prod deploy
                       |
                 Phase 6 (dev grafana) [parallel with 5]
                       |
                 Phase 7 (codebase sweep) <- requires Phase 3 done
                       |
                 Phase 8 (agent skill) [can start after Phase 1]
```

Phase 1 + 8 можно параллельно. Phase 3 + 4 можно параллельно. Phase 5 + 6 можно параллельно.

---

## Verification

### After Phase 2 (codex_core)
- `cd codex-core && python -m pytest`
- Dev: проверить colored output сохранился
- Prod sim: `DEBUG=False` → JSON в stdout, no colors

### After Phase 3-4 (middleware + metrics)
- `docker compose up` → `curl localhost:8001/health` → no log line в console
- `curl localhost:8001/metrics` → Prometheus metrics output
- Check `X-Request-ID` header в responses
- Grep logs for `request_id` field presence

### After Phase 5 (Alloy)
- SSH → `systemctl status alloy` → active
- Grafana Cloud → Explore → Loki → `{container="tbmmorpg-backend"}` → JSON parsed, labels visible
- Grafana Cloud → Explore → Prometheus → `http_requests_total{service="backend"}` → data present

### After Phase 6 (dev dashboard)
- `docker compose -f docker-compose.yml -f docker-compose.observability.yml up`
- `localhost:3000` → Grafana → dashboards auto-provisioned
- Generate traffic → verify graphs populate

### After Phase 7 (sweep)
- `grep -r 'logger.info(f"' src/` → 0 results
- `grep -r 'logger.warning(f"' src/` → 0 results
- Quality gate: `python -m pytest && python -m mypy src/`

## Critical Files

| File | Role |
|------|------|
| `codex-core/src/codex_core/common/loguru_setup.py` | Core logging setup — JSON prod sink, patcher |
| `codex-core/src/codex_core/common/log_context.py` | NEW — contextvars module |
| `src/shared/logging_config.py` | Project wrapper for codex_core |
| `src/shared/log_middleware.py` | NEW — HTTP request context |
| `src/shared/log_task_wrapper.py` | NEW — ARQ task context |
| `src/shared/metrics.py` | NEW — Prometheus registry |
| `src/shared/metrics_middleware.py` | NEW — HTTP metrics collection |
| `src/shared/metrics_endpoint.py` | NEW — /metrics route |
| `src/backend/app.py` | Backend entry — add middleware |
| `src/frontend/app.py` | Frontend entry — add middleware |
| `src/backend/chat/app.py` | Chat entry — add middleware + setup_logging |
| `src/backend/core/bus/producer.py` | Event bus — add metrics + structured logging |
| `deploy/alloy/config.alloy.prod` | NEW — Alloy reference config |
| `deploy/docker-compose.observability.yml` | NEW — dev Grafana + Prometheus |
| `docs/logging-rules.md` | NEW — logging rules document |
| `docs/planning/tasks/logging-sweep-task.md` | NEW — AI sweep task prompt |
| `docs/agent-skills/turnbasedmmorpg-logging-quality/SKILL.md` | NEW — agent skill |

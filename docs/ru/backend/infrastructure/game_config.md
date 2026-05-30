# Game Config

Game Config — Redis-backed слой runtime-настроек для баланса, таймингов,
лимитов и operational flags. Дефолты объявляются в коде через `BaseGameConfig`,
а Redis хранит только override-значения.

## Контракт

- Backend регистрирует namespace на старте и bootstrap пишет отсутствующие
  значения в Redis без перезаписи существующих override.
- API `/api/internal/config/{namespace}` отдает текущее значение, default,
  тип, признак изменения и metadata для админки: label, description, group,
  unit, range, step, risk, live_scope, tags.
- Запись через API валидирует тип и диапазон. Невалидное значение возвращает
  HTTP 422; неизвестный namespace/key возвращает 404.
- Runtime-код читает настройки через typed getters или feature-level tunables
  snapshot. Frontend не импортирует backend config-классы напрямую.

## Что хранить в Redis

Подходящие кандидаты:

- шансы, множители, caps, weights;
- TTL, timeout, interval, delay;
- лимиты очередей и page size, если они управляют runtime-поведением;
- feature flags для ops/training/runtime entry points.

Не переносить в Redis scalar config:

- security-параметры и пароли;
- имена Redis Streams events, task ids, queue names, API keys;
- версии схем, catalog version и asset paths;
- authored каталоги предметов, монстров, skills, feints, triggers, effects,
  loot profiles, world static locations и prompts.

Для структурных каталогов нужен отдельный catalog-admin/DB контракт с
schema-specific validation, а не универсальная scalar Redis-настройка.

## Audit

Для первичной инвентаризации:

```powershell
python tools/dev/game_config_audit.py
python tools/dev/game_config_audit.py --json
```

Скрипт классифицирует uppercase-константы как `runtime_config`,
`catalog_later`, `code_contract` или `ignore`. Решение о переносе остается за
владельцем feature: настройка должна иметь metadata, тест default-поведения и
тест Redis override.

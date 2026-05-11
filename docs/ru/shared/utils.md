# Utils

`src/shared/utils/` — dev-утилиты. Не используются в production-коде напрямую.

::: shared.utils.dev_utils
    options:
      show_source: false
      show_root_heading: false

## `dev_utils.log_debug_payload`

Рендерит произвольный payload (dict, list, Pydantic model) как Rich-таблицу и пишет одной строкой в loguru DEBUG — чтобы таблица не разбивалась на строки с таймстемпами.

```python
log_debug_payload("ArenaService.create", session_dto, enabled=settings.debug)
```

Параметр `enabled` позволяет отключить вызов в production не трогая код — достаточно передать `enabled=settings.debug`.

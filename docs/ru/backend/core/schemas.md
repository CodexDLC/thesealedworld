# Schemas

`src/backend/core/schemas/base.py` — два базовых Pydantic-класса.

| Класс | Назначение |
|-------|-----------|
| `BaseRequest` | Базовый класс для входящих схем. `populate_by_name=True` — разрешает алиасы и прямые имена полей одновременно |
| `BaseResponse` | Базовый класс для исходящих схем. `from_attributes=True` — позволяет создавать из ORM-объектов напрямую |

::: backend.core.schemas.base
    options:
      show_source: false
      show_root_heading: false

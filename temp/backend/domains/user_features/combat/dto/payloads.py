from pydantic import BaseModel


class ExchangePayload(BaseModel):
    """Данные для стратегии 'exchange' (Combat)."""

    target_id: int  # В обмене всегда одна конкретная цель (ID)

    # Финт (опционально)
    feint_id: str | None = None


class InstantPayload(BaseModel):
    """Данные для стратегии 'instant' (Abilities / Items)."""

    # В инстанте может быть ID, список ID или инструкция (TargetType)
    target_id: int | str | list[int] | None = None

    ability_id: str | None = None  # ID способности
    item_id: int | None = None  # ID предмета (если это расходник)
    feint_id: str | None = None  # ID финта (если это мгновенный финт, например "песок в глаза")

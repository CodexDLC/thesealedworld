"""
Модуль определяет планы запросов (Query Plans) для разных scope.
"""

QUERY_PLANS = {
    "full": ["attributes", "inventory", "skills", "vitals", "symbiote", "wallet"],
    "combats": ["attributes", "inventory", "skills", "vitals", "symbiote"],
    "status": ["attributes", "vitals", "symbiote"],
    "inventory": ["inventory", "wallet"],
    "exploration": ["attributes", "skills", "vitals"],
    # Будущие scope (закомментировать до реализации):
    # "trade": ["attributes", "inventory", "wallet"],
    # "tutorial": ["attributes", "vitals"],
}


def get_query_plan(scope: str) -> list[str]:
    """
    Возвращает список таблиц для загрузки на основе scope.
    По умолчанию возвращает план для 'full' (максимальный набор).

    Raises:
        ValueError: Если scope не поддерживается.
    """
    if scope not in QUERY_PLANS:
        # Fallback to 'full' if scope is invalid
        return QUERY_PLANS["full"]

    return QUERY_PLANS[scope]

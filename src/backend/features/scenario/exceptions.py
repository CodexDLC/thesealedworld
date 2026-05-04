from fastapi import status

from src.backend.core.exceptions import BaseAPIException


class ScenarioException(BaseAPIException):
    """Base exception for scenario feature"""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST, error_code: str = "scenario_error"):
        super().__init__(status_code=status_code, detail=detail, error_code=error_code)


class ScenarioSessionNotFound(ScenarioException):
    def __init__(self, char_id: int):
        super().__init__(
            detail=f"Активная сессия сценария для персонажа {char_id} не найдена.",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="scenario_session_missing",
        )


class ScenarioNodeNotFound(ScenarioException):
    def __init__(self, quest_key: str, node_key: str):
        super().__init__(
            detail=f"Узел '{node_key}' в квесте '{quest_key}' не найден.",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="scenario_node_missing",
        )


class InvalidScenarioAction(ScenarioException):
    def __init__(self, action_id: str):
        super().__init__(
            detail=f"Действие '{action_id}' недоступно или не существует в текущем контексте.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="scenario_invalid_action",
        )


class ScenarioConditionFailed(ScenarioException):
    def __init__(self, action_id: str):
        super().__init__(
            detail=f"Условия для выполнения действия '{action_id}' не выполнены.",
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="scenario_condition_failed",
        )


class ScenarioDirectorError(ScenarioException):
    def __init__(self, message: str):
        super().__init__(
            detail=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, error_code="scenario_director_panic"
        )


class ScenarioPoolEmpty(ScenarioException):
    def __init__(self, quest_key: str, pool_tag: str):
        super().__init__(
            detail=f"В пуле '{pool_tag}' (квест '{quest_key}') не найдено доступных узлов (или все они уже посещены).",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="scenario_pool_empty",
        )

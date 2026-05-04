from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CoreOrchestratorProtocol(Protocol):
    """
    Протокол для Core-оркестраторов, поддерживающих унифицированный вход.
    Позволяет CombatGateway вызывать их без знания специфики.
    """

    async def get_entry_point(self, char_id: int, action: str, context: dict[str, Any]) -> Any:
        """
        Единая точка входа в домен.

        Args:
            char_id: ID персонажа.
            action: Тип действия ('initialize', 'resume', 'view', etc.).
            context: Дополнительные данные (quest_key, session_id, etc.).

        Returns:
            DTO с данными для отображения (Payload).
        """
        ...

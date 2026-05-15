from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.features.generation_ai.handlers import AIGenerationTaskHandler


class AIGenerationTaskRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, AIGenerationTaskHandler] = {}

    def register(self, handler: AIGenerationTaskHandler) -> None:
        if not handler.task_type.strip():
            raise ValueError("AI generation handler task_type must not be empty")
        if handler.task_type in self._handlers:
            raise ValueError(f"AI generation handler already registered: {handler.task_type}")
        self._handlers[handler.task_type] = handler

    def resolve(self, task_type: str) -> AIGenerationTaskHandler:
        handler = self._handlers.get(task_type)
        if handler is None:
            raise KeyError(f"AI generation task handler is not registered: {task_type}")
        return handler

    def has(self, task_type: str) -> bool:
        return task_type in self._handlers

    @property
    def task_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

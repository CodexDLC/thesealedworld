from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.generation_ai.registry import AIGenerationTaskRegistry
from src.backend.features.items.tasks_ai import (
    register_generation_ai_tasks as register_item_generation_ai_tasks,
)
from src.backend.features.monsters.tasks_ai import (
    register_generation_ai_tasks as register_monster_generation_ai_tasks,
)
from src.backend.features.world.tasks_ai import (
    register_generation_ai_tasks as register_world_generation_ai_tasks,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def build_generation_ai_registry(*, session: AsyncSession | None = None) -> AIGenerationTaskRegistry:
    registry = AIGenerationTaskRegistry()
    register_item_generation_ai_tasks(registry, session=session)
    register_monster_generation_ai_tasks(registry, session=session)
    register_world_generation_ai_tasks(registry, session=session)
    return registry

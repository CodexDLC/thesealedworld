from __future__ import annotations

from typing import ClassVar

ConfigValue = int | float | str | bool


class BaseGameConfig:
    """Base class for feature-level game config blocks.

    Subclasses declare config keys as class-level attributes with their default values:

        class CombatConfig(BaseGameConfig):
            namespace = "combat"
            PARRY_SKILL_MULT_PER_POINT = 4.0
            CHAOS_DELAY_SECONDS = 300
    """

    namespace: ClassVar[str]

    @classmethod
    def defaults(cls) -> dict[str, ConfigValue]:
        return {
            k: v
            for k, v in vars(cls).items()
            if not k.startswith("_") and k != "namespace" and isinstance(v, (int, float, str, bool))
        }

    @classmethod
    def redis_key(cls, key: str) -> str:
        return f"game:config:{cls.namespace}:{key}"

    @classmethod
    def default_for(cls, key: str) -> ConfigValue | None:
        return cls.defaults().get(key)

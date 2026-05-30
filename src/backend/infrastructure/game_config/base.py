from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

ConfigValue = int | float | str | bool


@dataclass(frozen=True)
class ConfigEntryMeta:
    label: str | None = None
    description: str | None = None
    group: str | None = None
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    risk: str = "low"
    live_scope: str = "runtime"
    tags: tuple[str, ...] = ()
    choices: tuple[str, ...] = ()
    source: str = "code_default"

    @classmethod
    def from_raw(cls, raw: ConfigEntryMeta | dict[str, object] | None) -> ConfigEntryMeta:
        if raw is None:
            return cls()
        if isinstance(raw, ConfigEntryMeta):
            return raw
        tags = raw.get("tags", ())
        choices = raw.get("choices", ())
        return cls(
            label=_optional_str(raw.get("label")),
            description=_optional_str(raw.get("description")),
            group=_optional_str(raw.get("group")),
            unit=_optional_str(raw.get("unit")),
            min_value=_optional_float(raw.get("min_value")),
            max_value=_optional_float(raw.get("max_value")),
            step=_optional_float(raw.get("step")),
            risk=str(raw.get("risk") or "low"),
            live_scope=str(raw.get("live_scope") or "runtime"),
            tags=tuple(str(tag) for tag in tags) if isinstance(tags, (list, tuple, set)) else (),
            choices=tuple(str(choice) for choice in choices) if isinstance(choices, (list, tuple, set)) else (),
            source=str(raw.get("source") or "code_default"),
        )


class BaseGameConfig:
    """Base class for feature-level game config blocks.

    Subclasses declare config keys as class-level attributes with their default values:

        class CombatConfig(BaseGameConfig):
            namespace = "combat"
            PARRY_SKILL_MULT_PER_POINT = 4.0
            CHAOS_DELAY_SECONDS = 300
    """

    namespace: ClassVar[str]
    config_metadata: ClassVar[dict[str, ConfigEntryMeta | dict[str, object]]] = {}

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

    @classmethod
    def metadata_for(cls, key: str) -> ConfigEntryMeta:
        return ConfigEntryMeta.from_raw(cls.config_metadata.get(key))


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float | str) or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

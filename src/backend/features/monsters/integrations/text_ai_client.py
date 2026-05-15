from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, model_validator

from src.backend.config.settings import settings
from src.backend.features.monsters.prompts import build_monster_clan_flavor_prompt

if TYPE_CHECKING:
    from src.backend.core.ai import AIService

log = logging.getLogger(__name__)


class MonsterVariantFlavorDTO(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    appearance: str = Field(min_length=1, max_length=500)
    encounter: str = Field(default="", max_length=500)
    detected: str = Field(default="", max_length=500)
    ambush: str = Field(default="", max_length=500)
    idle: str = Field(default="", max_length=500)
    behavior: str = Field(default="", max_length=300)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_nested_flavor(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        flavor = value.get("flavor")
        if isinstance(flavor, dict):
            merged = dict(flavor)
            if value.get("name"):
                merged["name"] = value["name"]
            merged.update(
                {
                    key: raw
                    for key, raw in value.items()
                    if key in {"appearance", "encounter", "detected", "ambush", "idle", "behavior"}
                }
            )
            cls._fill_encounter_defaults(merged)
            return merged
        value = dict(value)
        cls._fill_encounter_defaults(value)
        return value

    @staticmethod
    def _fill_encounter_defaults(value: dict[str, Any]) -> None:
        encounter = value.get("encounter")
        detected = value.get("detected")
        ambush = value.get("ambush")
        idle = value.get("idle")
        behavior = value.get("behavior")
        if not detected and encounter:
            value["detected"] = encounter
        if not ambush and encounter:
            value["ambush"] = encounter
        if not idle and behavior:
            value["idle"] = behavior
        if not encounter and detected:
            value["encounter"] = detected


class MonsterClanFlavorDTO(BaseModel):
    name_ru: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=1200)
    variants_flavor: dict[str, MonsterVariantFlavorDTO] = Field(default_factory=dict)


class MonsterClanTextAIClient:
    prompt_name = "monster_clan_flavor"
    _rate_limit_lock: asyncio.Lock | None = None
    _last_request_monotonic: float | None = None
    _blocked_until_monotonic: float | None = None
    _failure_backoff_seconds: float = 0.0

    def __init__(self, ai: AIService | None) -> None:
        self.ai = ai

    async def generate_clan_flavor(self, payload: dict[str, Any]) -> MonsterClanFlavorDTO | None:
        if self.ai is None:
            return None
        if not await self._wait_for_rate_limit():
            return None
        try:
            generated = await self.ai.generate_json(
                build_monster_clan_flavor_prompt(payload),
                schema=MonsterClanFlavorDTO,
            )
        except Exception:
            self._apply_failure_backoff()
            log.exception("Monster clan flavor AI request failed; using fallback flavor")
            return None
        self._reset_failure_backoff()
        if isinstance(generated, MonsterClanFlavorDTO):
            return generated
        return MonsterClanFlavorDTO.model_validate(generated)

    @classmethod
    async def _wait_for_rate_limit(cls) -> bool:
        interval = max(0.0, float(settings.monster_clan_flavor_ai_interval_seconds))
        if interval <= 0.0:
            return True

        lock = cls._rate_limit_lock
        if lock is None:
            lock = asyncio.Lock()
            cls._rate_limit_lock = lock

        async with lock:
            now = time.monotonic()
            if cls._blocked_until_monotonic is not None and now < cls._blocked_until_monotonic:
                remaining = cls._blocked_until_monotonic - now
                log.info("Monster clan flavor AI cooldown active; skipping request for %.2fs", remaining)
                return False
            if cls._last_request_monotonic is not None:
                wait_seconds = interval - (now - cls._last_request_monotonic)
                if wait_seconds > 0:
                    log.info("Monster clan flavor AI rate limited; sleeping %.2fs", wait_seconds)
                    await asyncio.sleep(wait_seconds)
            cls._last_request_monotonic = time.monotonic()
            return True

    @classmethod
    def _apply_failure_backoff(cls) -> None:
        interval = max(0.0, float(settings.monster_clan_flavor_ai_interval_seconds))
        if cls._failure_backoff_seconds <= 0.0:
            cls._failure_backoff_seconds = interval
        else:
            cls._failure_backoff_seconds += 10.0
        cls._blocked_until_monotonic = time.monotonic() + cls._failure_backoff_seconds
        log.warning("Monster clan flavor AI blocked for %.2fs after failure", cls._failure_backoff_seconds)

    @classmethod
    def _reset_failure_backoff(cls) -> None:
        cls._failure_backoff_seconds = 0.0
        cls._blocked_until_monotonic = None

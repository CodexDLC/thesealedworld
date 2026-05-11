from dataclasses import dataclass, field

from fastapi import Request


@dataclass(frozen=True)
class CombatStats:
    active: int
    completed: int
    total: int
    recent: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class CombatSettingEntry:
    name: str
    value: str
    source: str


COMBAT_SETTINGS: tuple[CombatSettingEntry, ...] = (
    CombatSettingEntry("PARRY_SKILL_MULT_PER_POINT", "4.0", "resolver.py"),
    CombatSettingEntry("SHIELD_BLOCK_SKILL_MULT_PER_POINT", "1.5", "resolver.py"),
    CombatSettingEntry("SHIELD_MASTERY_ABSORB_RATIO_PER_PT", "0.20", "resolver.py"),
    CombatSettingEntry("SHIELD_ABSORB_RATIO_CAP", "0.85", "resolver.py"),
    CombatSettingEntry("UNARMED_MIN_EFFICIENCY", "0.5", "resolver.py"),
    CombatSettingEntry("UNARMED_MAX_EFFICIENCY", "3.0", "resolver.py"),
    CombatSettingEntry("UNARMED_NOVICE_SPREAD", "0.5", "resolver.py"),
    CombatSettingEntry("UNARMED_MASTER_SPREAD", "0.1", "resolver.py"),
    CombatSettingEntry("CHAOS_FIRST_CHECK_DELAY_SECONDS", "300", "chaos_service.py"),
)


class CombatCabinetService:
    async def get_stats(self, request: Request) -> CombatStats:
        # MVP: counters from app state tracked at runtime; real DB query added with backend endpoint
        counters: dict[str, int] = getattr(request.app.state, "site_analytics", {})
        return CombatStats(
            active=counters.get("combat_active", 0),
            completed=counters.get("combat_completed", 0),
            total=counters.get("combat_total", 0),
            recent=[],
        )

    def get_settings(self) -> tuple[CombatSettingEntry, ...]:
        return COMBAT_SETTINGS

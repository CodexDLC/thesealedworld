from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.generation import MonsterGroupMemberPreview, MonsterGroupResult


@dataclass(frozen=True, slots=True)
class ProjectedMonsterIntelGroup:
    level: int
    count: int
    danger_band: str
    total_power: int | None
    enemies: list[ProjectedMonsterIntelEnemy]

    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
        return {
            "level": self.level,
            "count": self.count,
            "danger_band": self.danger_band,
            "total_power": self.total_power,
            "enemies": [enemy.model_dump(mode=mode) for enemy in self.enemies],
        }


@dataclass(frozen=True, slots=True)
class ProjectedMonsterIntelEnemy:
    name: str
    description: str
    role: str
    variant_key: str
    member_tier: int | None
    threat_rating: int | None
    hp_percent: int | None
    image: str | None
    visual: dict[str, Any]
    monster_id: str | None
    tags: list[str]
    intel: dict[str, Any]

    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
        del mode
        return {
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "variant_key": self.variant_key,
            "member_tier": self.member_tier,
            "level": self.member_tier,
            "threat_rating": self.threat_rating,
            "hp_percent": self.hp_percent,
            "image": self.image,
            "visual": self.visual,
            "monster_id": self.monster_id,
            "tags": self.tags,
            "intel": self.intel,
        }


class MonsterIntelProjector:
    """Builds player-facing monster intel from group previews without exposing raw combat data."""

    def project_group(self, group: MonsterGroupResult, *, hunting_skill: Any) -> ProjectedMonsterIntelGroup:
        level = hunting_intel_level(hunting_skill)
        danger_band = _danger_band(group.total_power, reference=max(1.0, float(group.adjusted_budget or 1.0)))
        return ProjectedMonsterIntelGroup(
            level=level,
            count=len(group.previews),
            danger_band=danger_band,
            total_power=group.total_power if level >= 4 else None,
            enemies=[self.project_enemy(preview, level=level, group=group) for preview in group.previews],
        )

    def project_enemy(
        self,
        preview: MonsterGroupMemberPreview,
        *,
        level: int,
        group: MonsterGroupResult,
    ) -> ProjectedMonsterIntelEnemy:
        show_identity = level >= 1
        show_vitals = level >= 2
        show_profile = level >= 3
        show_expert = level >= 4

        hp_percent = _hp_percent(preview.vitals.get("hp") or preview.hp) if show_vitals else None
        gear_score = _optional_int(preview.gear_score)
        enemy_danger = _danger_band(gear_score or 0, reference=max(1.0, float(group.adjusted_budget or 1.0)))
        intel = {
            "level": level,
            "danger_band": enemy_danger if show_vitals else "???",
            "power": {
                "label": _power_label(enemy_danger) if show_vitals else "???",
                "gear_score": gear_score if show_expert else None,
            },
            "vitals": _vitals(preview) if show_vitals else {},
            "profile": _profile(preview) if show_profile else {},
            "equipment": _equipment(preview) if show_profile else [],
            "affixes": _affixes(preview) if show_expert else [],
            "traits": sorted(set(preview.tags)) if show_profile else [],
            "group": {
                "count": len(group.previews),
                "danger_band": _danger_band(
                    group.total_power,
                    reference=max(1.0, float(group.adjusted_budget or 1.0)),
                )
                if show_vitals
                else "???",
                "total_power": group.total_power if show_expert else None,
                "target_budget": group.target_budget if show_expert else None,
                "adjusted_budget": group.adjusted_budget if show_expert else None,
            },
        }
        return ProjectedMonsterIntelEnemy(
            name=preview.name if show_identity else "???",
            description=preview.description if show_identity else "???",
            role=preview.role if show_identity else "???",
            variant_key=preview.variant_key if show_identity else "???",
            member_tier=preview.member_tier if show_identity else None,
            threat_rating=None,
            hp_percent=hp_percent,
            image=preview.image,
            visual=dict(preview.visual),
            monster_id=preview.monster_id if show_identity else None,
            tags=sorted(set(preview.tags)) if show_profile else [],
            intel=intel,
        )


def hunting_intel_level(value: Any) -> int:
    normalized = _normalized_skill(value)
    if normalized >= 0.8:
        return 4
    if normalized >= 0.6:
        return 3
    if normalized >= 0.4:
        return 2
    if normalized >= 0.2:
        return 1
    return 0


def _normalized_skill(value: Any) -> float:
    try:
        raw = max(0.0, float(value or 0.0))
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, raw / 100.0 if raw > 1.0 else raw)


def _vitals(preview: MonsterGroupMemberPreview) -> dict[str, dict[str, int | str]]:
    raw = dict(preview.vitals or {})
    hp = dict(raw.get("hp") or preview.hp or {})
    return {
        key: value
        for key, value in {
            "hp": _vital(hp),
            "energy": _vital(dict(raw.get("energy") or {})),
            "concentration": _vital(dict(raw.get("concentration") or raw.get("stamina") or {})),
        }.items()
        if value
    }


def _vital(raw: dict[str, Any]) -> dict[str, int | str]:
    current = _optional_int(
        raw.get("current") or raw.get("cur") or raw.get("value") or raw.get("hp") or raw.get("stamina")
    )
    maximum = _optional_int(raw.get("max") or raw.get("maximum") or raw.get("max_hp") or raw.get("max_stamina"))
    if current is None or maximum is None:
        return {}
    return {"current": current, "max": maximum, "label": f"{current}/{maximum}"}


def _hp_percent(raw: Any) -> int | None:
    hp = dict(raw or {}) if isinstance(raw, dict) else {}
    current = _optional_int(hp.get("current") or hp.get("cur") or hp.get("hp") or hp.get("hp_current"))
    maximum = _optional_int(hp.get("max") or hp.get("max_hp") or hp.get("hp_max"))
    if current is None or not maximum:
        return None
    return max(0, min(100, round(current / maximum * 100)))


def _profile(preview: MonsterGroupMemberPreview) -> dict[str, str]:
    return {
        key: value
        for key, value in {
            "archetype": preview.archetype,
            "family_id": preview.family_id,
            "organization_type": preview.organization_type,
        }.items()
        if value
    }


def _equipment(preview: MonsterGroupMemberPreview) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in preview.equipment:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "slot": str(item.get("slot") or "unknown"),
                "kind": str(item.get("kind") or item.get("item_type") or "item"),
                "label": str(item.get("label") or item.get("base_id") or item.get("item_id") or "unknown"),
                "tags": [str(tag) for tag in item.get("tags", []) if tag] if isinstance(item.get("tags"), list) else [],
            }
        )
    return rows


def _affixes(preview: MonsterGroupMemberPreview) -> list[dict[str, Any]]:
    return [dict(item) for item in preview.affixes if isinstance(item, dict)]


def _danger_band(value: int | float, *, reference: float) -> str:
    if reference <= 0:
        reference = 1.0
    ratio = max(0.0, float(value or 0.0)) / reference
    if ratio >= 1.2:
        return "смертельная"
    if ratio >= 0.8:
        return "высокая"
    if ratio >= 0.45:
        return "средняя"
    return "низкая"


def _power_label(danger_band: str) -> str:
    return {
        "низкая": "низкая угроза",
        "средняя": "средняя угроза",
        "высокая": "высокая угроза",
        "смертельная": "смертельная угроза",
    }.get(danger_band, "???")


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = ["MonsterIntelProjector", "ProjectedMonsterIntelEnemy", "ProjectedMonsterIntelGroup", "hunting_intel_level"]

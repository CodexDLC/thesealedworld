from __future__ import annotations

from pydantic import BaseModel, Field


class MonsterLootCultureDTO(BaseModel):
    craft_style: str = Field(min_length=1, max_length=300)
    craft_skill_hint: str = Field(min_length=1, max_length=500)
    salvage_sources: list[str] = Field(default_factory=list, max_length=12)
    tone_hints: list[str] = Field(default_factory=list, max_length=12)
    equipment_origin_notes: list[str] = Field(default_factory=list, max_length=12)


def default_loot_culture_payload(*, family_id: str, archetype: str, organization_type: str) -> dict[str, object]:
    if archetype == "humanoid":
        return {
            "craft_style": "практичная переделка найденного и украденного снаряжения",
            "craft_skill_hint": "используют то, что удалось снять, починить, связать ремнями или грубо подогнать под бой",
            "salvage_sources": ["украденное оружие", "разобранная броня", "городской лом"],
            "tone_hints": ["практичность выживальщиков", "следы ремонта", "вещь могла переходить из рук в руки"],
            "equipment_origin_notes": [f"снаряжение связано с {organization_type} {family_id}"],
        }
    if archetype == "beast":
        return {
            "craft_style": "естественные останки и трофейные части вместо ремесла",
            "craft_skill_hint": "предметы выглядят как выделанные шкуры, кости, когти или грубые трофеи охотника",
            "salvage_sources": ["шкура", "кость", "когти", "зубы"],
            "tone_hints": ["звериная грубость", "следы охоты", "сырой природный материал"],
            "equipment_origin_notes": [f"материал связан с существами {family_id}"],
        }
    return {
        "craft_style": "снаряжение отражает происхождение семьи",
        "craft_skill_hint": "использует доступные семье материалы и привычные способы переделки",
        "salvage_sources": ["местные трофеи", "обломки окружения"],
        "tone_hints": ["следы происхождения", "локальная переделка"],
        "equipment_origin_notes": [f"предмет несет стиль {organization_type} {family_id}"],
    }

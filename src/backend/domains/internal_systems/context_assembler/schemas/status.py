from typing import Any

from pydantic import computed_field

from src.backend.domains.internal_systems.context_assembler.schemas.base import BaseTempContext


class StatusTempContext(BaseTempContext):
    """
    Контекст для экрана персонажа.
    """

    @computed_field(alias="stats_display")
    def stats_view(self) -> dict[str, Any]:
        if not self.core_attributes:
            return {}

        stats = {}
        # Пример маппинга (можно расширить)
        stat_labels = {
            "strength": "Сила",
            "agility": "Ловкость",
            "endurance": "Выносливость",
            "intelligence": "Интеллект",
            "wisdom": "Мудрость",
            "men": "Ментальность",
            "perception": "Восприятие",
            "charisma": "Харизма",
            "luck": "Удача",
        }

        for stat_key, label in stat_labels.items():
            value = getattr(self.core_attributes, stat_key, 0)
            stats[stat_key] = {"value": value, "label": label}

        return stats

    @computed_field(alias="vitals_display")
    def vitals_view(self) -> dict[str, Any]:
        if not self.core_vitals:
            return {
                "hp": {"current": 0, "max": 0, "percent": 0},
                "energy": {"current": 0, "max": 0, "percent": 0},
            }

        hp_cur = self.core_vitals.get("hp", {}).get("cur", 0)
        hp_max = self.core_vitals.get("hp", {}).get("max", 1)
        en_cur = self.core_vitals.get("energy", {}).get("cur", 0)
        en_max = self.core_vitals.get("energy", {}).get("max", 1)

        return {
            "hp": {
                "current": hp_cur,
                "max": hp_max,
                "percent": int((hp_cur / hp_max) * 100) if hp_max > 0 else 0,
            },
            "energy": {
                "current": en_cur,
                "max": en_max,
                "percent": int((en_cur / en_max) * 100) if en_max > 0 else 0,
            },
        }

    @computed_field(alias="symbiote_info")
    def symbiote_view(self) -> dict[str, Any]:
        if not self.core_symbiote:
            return {"name": "Неизвестно", "gift": None, "rank": 0}

        return {
            "name": self.core_symbiote.get("symbiote_name", "Симбиот"),
            "gift": self.core_symbiote.get("gift_id"),
            "rank": self.core_symbiote.get("gift_rank", 0),
        }

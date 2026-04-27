from typing import Any, cast

from pydantic import BaseModel, computed_field

# Импортируем хелпер, который уже умеет считать шмот монстра
from src.backend.domains.internal_systems.context_assembler.logic.helpers.monster_data_helper import (
    get_equipment_modifiers,
)


class MonsterTempContextSchema(BaseModel):
    """
    Слепок контекста МОНСТРА в Redis.
    Структура вывода (JSON) полностью совпадает с TempContextSchema игрока
    в части 'math_model' и 'vitals', чтобы LifecycleService не видел разницы.
    """

    # --- 1. CORE DATA (Источник правды) ---
    # Храним исходные словари из ORM
    core_stats: dict[str, Any]  # scaled_base_stats
    core_loadout: dict[str, Any]  # loadout_ids
    core_skills: list[Any] | dict[str, Any]  # skills_snapshot (может быть dict или list)
    core_meta: dict[str, Any]  # {name, role, threat, clan_id}

    # --- 2. COMPUTED VIEWS (Проекции) ---

    @computed_field(alias="math_model")
    def combat_view(self) -> dict[str, Any]:
        """
        Генерирует v:raw матрицу, идентичную структуре игрока.
        """
        model: dict[str, Any] = {
            "attributes": {},
            "modifiers": {},
            "tags": ["monster", self.core_meta.get("role", "minion")],
        }

        # 1. Base Attributes (из scaled_base_stats)
        # У монстра статы уже в словаре, просто перекладываем
        for stat, val in self.core_stats.items():
            if val:
                model["attributes"][stat] = {"base": str(val), "flats": {}, "percents": {}}

        # 2. Equipment Modifiers
        # Используем существующий хелпер, он возвращает уже сгруппированные данные
        # Но нам нужно разложить их в нашу структуру v:raw
        equip_mods = get_equipment_modifiers(self.core_loadout)

        for stat, data in equip_mods.items():
            # data может быть dict или чем-то еще, приводим к dict
            data_dict = cast(dict[str, Any], data) if isinstance(data, dict) else {}
            sources: dict[str, Any] = data_dict.get("sources", {})

            # Если это атрибут (сила, ловкость) -> в attributes.flats
            if stat in model["attributes"]:
                for src, val in sources.items():
                    model["attributes"][stat]["flats"][src] = val

            # Если это вторичный стат (урон, броня) -> в modifiers.sources
            else:
                if stat not in model["modifiers"]:
                    model["modifiers"][stat] = {"sources": {}}

                for src, val in sources.items():
                    model["modifiers"][stat]["sources"][src] = val

        return model

    @computed_field(alias="loadout")
    def loadout_view(self) -> dict[str, Any]:
        """
        Проекция арсенала.
        У монстров нет пояса, но есть абилки.
        """
        # Превращаем скиллы в список строк ID
        ability_ids = []

        # Обработка skills_snapshot (может быть dict или list)
        iterable = self.core_skills
        if isinstance(self.core_skills, dict):
            iterable = list(self.core_skills.keys())  # Если dict {id: lvl}, берем ключи

        for s in iterable:
            if isinstance(s, dict) and "id" in s:
                ability_ids.append(str(s["id"]))
            else:
                ability_ids.append(str(s))

        return {
            "belt": [],  # Монстры не пьют банки (пока)
            "abilities": ability_ids,
            "skills": [],  # Совместимость с игроком
        }

    @computed_field(alias="vitals")
    def vitals_view(self) -> dict[str, Any]:
        """
        Монстры всегда заходят фуловыми или -1 (авторасчет).
        """
        return {
            "hp_current": -1,  # Сигнал для Lifecycle: "Посчитай от макс. ХП"
            "energy_current": -1,
        }

    @computed_field(alias="meta")
    def meta_view(self) -> dict[str, Any]:
        return {
            "entity_id": str(self.core_meta.get("id")),
            "type": "monster",
            "name": self.core_meta.get("name_ru", self.core_meta.get("name")),  # name_ru приоритетнее
            "role": self.core_meta.get("role"),
            "timestamp": 0,
        }

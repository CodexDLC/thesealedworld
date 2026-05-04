# 💾 Schema: Skills (Навыки)

[⬅️ Назад: Data Schemas](./README.md) | [📖 Правила: Skills](../Skills/README.md)

---

## 📋 Обзор
Техническая реализация хранения навыков.
Навыки используются как **коэффициенты** в формулах боя и крафта.

## ⚙️ DTO Structure

```python
from pydantic import BaseModel
from enum import Enum

class SkillCategory(str, Enum):
    COMBAT = "combat"
    NON_COMBAT = "non_combat"

class SkillGroup(str, Enum):
    WEAPON_MASTERY = "weapon_mastery"
    ARMOR = "armor"
    TACTICAL = "tactical"
    COMBAT_SUPPORT = "combat_support"
    GATHERING = "gathering"
    CRAFTING = "crafting"
    TRADE = "trade"
    SOCIAL = "social"
    SURVIVAL = "survival"

class SkillDTO(BaseModel):
    skill_key: str              # Уникальный ключ (например, "skill_swords")
    name_en: str                # Название (EN)
    name_ru: str                # Название (RU)
    
    category: SkillCategory     # Категория
    group: SkillGroup           # Группа
    
    # Математика прогрессии (влияет на скорость прокачки)
    stat_weights: dict[str, int] # Веса атрибутов {"strength": 2, "agility": 1}
    rate_mod: float             # Множитель скорости (1.0 = стандарт)
    wall_mod: float             # Множитель сложности капа (1.0 = стандарт)
    
    description: str            # Описание для UI
```

## 📝 Пример JSON/Dict
```python
swords_config = {
    "skill_key": "skill_swords",
    "name_en": "Swordsmanship",
    "name_ru": "Владение мечами",
    "category": "combat",
    "group": "weapon_mastery",
    "stat_weights": {"strength": 2, "agility": 1, "endurance": 1},
    "rate_mod": 1.0,
    "wall_mod": 1.0,
    "description": "Мастерство владения мечами. Повышает точность и стабилизирует урон."
}
```

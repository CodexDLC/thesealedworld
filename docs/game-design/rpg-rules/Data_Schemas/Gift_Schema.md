# 💾 Schema: Gifts (Дары)

[⬅️ Назад: Data Schemas](./README.md) | [📖 Правила: Gifts](../Gifts/README.md)

---

## 📋 Обзор
Техническая реализация Даров (Gifts) — магических классов персонажа.

## ⚙️ DTO Structure

```python
from pydantic import BaseModel
from enum import Enum

class GiftSchool(str, Enum):
    FIRE = "fire"
    WATER = "water"
    AIR = "air"
    EARTH = "earth"
    LIGHT = "light"
    DARKNESS = "darkness"
    NATURE = "nature"
    ARCANE = "arcane"

class GiftDTO(BaseModel):
    gift_id: str                # "gift_true_fire"
    name_ru: str                # "Истинное Пламя"
    school: GiftSchool          # FIRE

    description: str
    role: str                   # "Damage Dealer", "Tank", etc.

    # Способности, открывающиеся по мере прокачки
    # Level -> List[AbilityID]
    abilities_progression: dict[int, list[str]] = {}

    # Пассивные бонусы (опционально)
    # Level -> Modifiers
    passives_progression: dict[int, dict] = {}
```

## 📝 Пример: True Fire
```python
true_fire_config = {
    "gift_id": "gift_true_fire",
    "name_ru": "Истинное Пламя",
    "school": "fire",
    "description": "Твой огонь не требует топлива. Классический боевой пирокинез.",
    "role": "Damage Dealer",
    "abilities_progression": {
        1: ["fireball"],
        3: ["flame_thrower"],
        5: ["inferno_blast"]
    }
}
```

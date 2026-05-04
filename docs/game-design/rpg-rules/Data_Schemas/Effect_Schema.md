# 💾 Schema: Effects (Эффекты)

[⬅️ Назад: Data Schemas](./README.md) | [🧠 Логика работы](../../Domains/User_Features/Combat/Mechanics/Effects_Logic.md)

---

## 📋 Обзор
Техническое описание структур данных для системы Эффектов.
Подробное описание механики см. в [Effects Logic](../../Domains/User_Features/Combat/Mechanics/Effects_Logic.md).

---

## ⚙️ 1. Library Structure (EffectDTO)
Описывает "Рецепт" эффекта. Хранится в `GameData`.

```python
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class EffectType(str, Enum):
    DOT = "dot"                 # Урон со временем (HP/EN)
    HOT = "hot"                 # Лечение со временем (HP/EN)
    BUFF = "buff"               # Плюс к статам
    DEBUFF = "debuff"           # Минус к статам
    CONTROL = "control"         # Стан, Сон, Слепота (Логика)

class ControlInstructionDTO(BaseModel):
    """
    Инструкции поведения для эффектов контроля.
    """
    # Имя флага состояния (для UI/AI и проверок)
    status_name: str 

    # Инструкции для Атакующего (Source)
    # Ключи: "can_act", "accuracy_mult", "damage_deal_mult"
    source_behavior: dict[str, Any] = Field(default_factory=dict)

    # Инструкции для Защитника (Target)
    # Ключи: "can_dodge", "can_block", "force_hit", "damage_taken_mult"
    target_behavior: dict[str, Any] = Field(default_factory=dict)

class EffectDTO(BaseModel):
    effect_id: str
    name_ru: str
    description_ru: str
    
    type: EffectType
    duration: int               # Базовая длительность

    # --- 1. Ресурсы (DOT/HOT) ---
    # Базовое значение за ход.
    resource_impact: dict[str, int] = Field(default_factory=dict)

    # --- 2. Статы (BUFF/DEBUFF) ---
    # Значения, которые добавляются в temp modifiers.
    raw_modifiers: dict[str, float] = Field(default_factory=dict)

    # --- 3. Логика (CONTROL) ---
    # Инструкции поведения.
    control_logic: ControlInstructionDTO | None = None

    # Теги (для диспела/иммунитета)
    tags: list[str] = Field(default_factory=list)
```

---

## ⚙️ 2. Application Params (EffectParams)
Структура параметров, передаваемых при наложении эффекта (из Абилки или Триггера).

```python
class EffectParams(TypedDict, total=False):
    """
    Параметры для EffectFactory.
    """
    # Переопределение длительности
    duration: int
    
    # Множитель силы (для Impact и Bleed)
    power: float           
    
    # Прямое задание ресурсов (редко, переопределяет конфиг)
    impact: dict[str, int] 
    
    # Динамические статы (для Buff, добавляются к конфигу)
    mutations: dict[str, Any]
    
    # Кастомный контроль (редко)
    control: dict[str, Any]
    
    # Условия снятия
    remove_on: list[str]
```

---

## ⚙️ 3. Instance Structure (ActiveEffectDTO)
Описывает конкретный эффект на персонаже.

```python
class ActiveEffectDTO(BaseModel):
    uid: str                    # Уникальный ID инстанса
    effect_id: str              # Ссылка на конфиг
    source_id: int              # ID того, кто наложил
    expire_at_exchange: int     # Таймер
    
    # --- State ---
    impact: dict[str, int] = {} # Копия resource_impact (с учетом power)
    
    # Копия control_logic из конфига
    control: ControlInstructionDTO | None = None
    
    # Исходный множитель силы (для наследования)
    power: float = 1.0
    
    # Исходные параметры создания (для наследования и логики)
    params: dict[str, Any] = {}
    
    # --- Memory (для отката) ---
    # Список ключей в actor.raw.modifiers, которые этот эффект изменил.
    modified_keys: list[str] = Field(default_factory=list)
```

---

## 📝 Примеры JSON (Library)

### 1. Яд (DOT)
```json
{
  "effect_id": "poison_weak",
  "name_ru": "Слабый Яд",
  "type": "dot",
  "duration": 3,
  "resource_impact": {
    "hp": -10
  },
  "description_ru": "Наносит 10 урона каждый ход."
}
```

### 2. Сила Медведя (BUFF)
```json
{
  "effect_id": "bear_strength",
  "name_ru": "Сила Медведя",
  "type": "buff",
  "duration": 3,
  "raw_modifiers": {
    "strength": 5.0,
    "physical_damage_mult": 0.1
  },
  "description_ru": "Увеличивает Силу на 5 и Физ. урон на 10%."
}
```

### 3. Оглушение (CONTROL)
```json
{
  "effect_id": "stun",
  "name_ru": "Оглушение",
  "type": "control",
  "duration": 1,
  "control_logic": {
    "status_name": "is_stun",
    "source_behavior": {
      "can_act": false
    },
    "target_behavior": {
      "can_dodge": false,
      "force_hit": true
    }
  },
  "description_ru": "Персонаж не может действовать и уклоняться."
}
```

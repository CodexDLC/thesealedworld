# 💾 Schema: Triggers (Триггеры и Правила)

[⬅️ Назад: Data Schemas](./README.md) | [🧠 Логика работы](../../Domains/User_Features/Combat/Mechanics/Triggers_Logic.md)

---

## 📋 Обзор
Техническое описание структур данных для системы Триггеров.
Подробное описание механики см. в [Triggers Logic](../../Domains/User_Features/Combat/Mechanics/Triggers_Logic.md).

---

## ⚙️ 1. Структура Правила (TriggerDTO)
Описывает "Что сделать, если событие произошло". Хранится в `TRIGGER_RULES`.

```python
class TriggerDTO(BaseModel):
    id: str                     # Уникальный ID (ключ для активации)
    name_ru: str                # Для логов и UI
    
    event: str                  # Когда срабатывает (ON_CRIT, ON_DODGE...)
    chance: float = 1.0         # Шанс срабатывания (если правило активно)
    
    # Изменения, которые вносит правило
    # Ключи: 
    # - "force.hit_evasion": Изменение флага
    # - "add_effect": Наложение эффекта (значение - словарь с id и params)
    mutations: dict[str, Any] = {} 
```

---

## ⚙️ 2. Активация (TriggerRulesFlagsDTO)
Описывает "Какие правила включены в текущем ударе".
Это вложенная структура, повторяющая этапы Резолвера.

```python
class TriggerRulesFlagsDTO(BaseModel):
    # 1. Точность
    accuracy: AccuracyTriggersDTO   # {true_strike: bool, ...}
    
    # 2. Крит
    crit: CritTriggersDTO           # {bleed_on_crit: bool, ...}
    
    # 3. Защита
    dodge: DodgeTriggersDTO         # {counter_on_dodge: bool}
    parry: ParryTriggersDTO         # {disarm_on_parry: bool}
    block: BlockTriggersDTO         # {bash_on_block: bool}
    
    # 4. Контроль (Финал)
    control: ControlTriggersDTO     # {stun_on_hit: bool}
    
    # 5. Урон
    damage: DamageTriggersDTO       # {execute_low_hp: bool}
```

---

## 📝 Примеры JSON (Trigger Definitions)

### True Strike (Верный удар)
```python
TriggerDTO(
    id="true_strike",
    event="ON_ACCURACY_CHECK",
    mutations={
        "force.hit_evasion": True # Отключает возможность уворота
    }
)
```

### Bleed on Crit (Кровотечение при крите)
```python
TriggerDTO(
    id="bleed_on_crit",
    event="ON_CRIT",
    mutations={
        "add_effect": {
            "id": "bleed",
            "params": {
                "power": 1.0 # Сила кровотока (скалируется от урона)
            }
        }
    }
)
```

# 🛠️ Combat Config Guide (Справочник Геймдизайнера)

Этот документ описывает, как настраивать боевую систему: создавать Финты, Триггеры, Эффекты и Оружие.

---

## 🧠 1. Философия Системы

Бой строится на **Пайплайне** (Pipeline) — последовательности этапов (Точность -> Защита -> Урон).
Мы управляем этим процессом через **Флаги** и **Триггеры**.

*   **Флаг (Flag):** Рычаг управления. (Пример: `force.crit` — "Всегда крит").
*   **Триггер (Trigger):** Правило "Если X, то включи Флаг". (Пример: "Если Крит, то включи Игнор Брони").
*   **Мутация (Mutation):** Изменение числа. (Пример: "Урон +50%").

---

## 📅 2. События (Events)

В эти моменты можно активировать Триггеры:

| Событие | Описание | Примеры использования |
| :--- | :--- | :--- |
| **ON_ACCURACY_CHECK** | Проверка точности (до броска) | True Strike, Игнор Блока (Стиль 2H) |
| **ON_MISS** | Промах | Rage on Miss (Накопление ярости) |
| **ON_CRIT** | Успешный крит | Bleed on Crit, Stun on Crit |
| **ON_DODGE** | Враг уклонился | Counter on Dodge (Контратака) |
| **ON_PARRY** | Враг парировал | Disarm on Parry (Обезоруживание) |
| **ON_BLOCK** | Враг заблокировал | Shield Reflect (Отражение), Bash on Block |
| **ON_CHECK_CONTROL** | Конец хода (если попал) | Stun on Hit, Knockdown |

---

## 🚩 3. Доступные Флаги (Flags)

Эти ключи можно использовать в `mutations` (в Финтах и Триггерах).

### 🔹 Force (Принуждение)
*   `force.hit`: Гарантированное попадание (пропуск Accuracy).
*   `force.crit`: Гарантированный крит.
*   `force.hit_evasion`: Запрет уклонения (враг не может увернуться).
*   `force.miss`: Гарантированный промах.

### 🔹 Restriction (Запреты)
*   `restriction.cannot_crit`: Запрет крита.
*   `restriction.ignore_block`: Игнорирование щита (Block = 0).
*   `restriction.ignore_parry`: Игнорирование парирования.

### 🔹 Formula (Изменение формул)
*   `formula.can_pierce`: Игнорирование брони (Armor = 0).
*   `formula.crit_damage_boost`: Включить бонус урона крита (x1.5).
*   `formula.evasion_halved`: Шанс уворота врага / 2.
*   `formula.parry_halved`: Шанс парирования врага / 2.
*   `formula.block_halved`: Шанс блока врага / 2.
*   `formula.force_shield_defense_branch`: Успешный block щитом всегда идет в защитную ветку.
*   `formula.force_shield_counter_branch`: Успешный block щитом всегда идет в контр-ветку.
*   `formula.shield_branch_invert`: Меняет местами веса defensive/counter ветки щита.
*   `formula.shield_counter_from_absorbed`: Контр-ветка считает возврат от мощности контакта, а не от сырого power щита.

### 🔹 State (Состояние)
*   `state.check_counter`: Запустить проверку контратаки.

### 🔹 Chain Events (Цепные реакции)
*   `chain_events.trigger_offhand_attack`: Доп. атака второй рукой.

---

## 🔢 4. Мутации Чисел (Raw Mutations)

Используются в Финтах (`raw_mutations`) для изменения статов.
Поддерживают строки для калькулятора: `"+10"`, `"-20%"`, `"*1.5"`.

*   `accuracy_mult`: Множитель точности.
*   `shield_block_chance_mult`: Множитель шанса события block щитом.
*   `shield_guard_power_mult`: Множитель power щита для защитной ветки.
*   `shield_counter_power_mult`: Множитель возврата для контр-ветки щита.
*   `physical_damage_mult`: Множитель физ. урона.
*   `crit_chance`: Шанс крита.
*   `dodge_chance`: Шанс уворота.

---

## 🧪 5. Эффекты (Effects)

Команда `add_effect` используется в Триггерах для наложения статусов.

```python
"add_effect": {
    "id": "bleed",          # ID эффекта
    "params": {             # Опционально
        "duration": 2,
        "power": 30
    }
}
```

---

## 🍳 6. Примеры (Cookbook)

### 🗡️ "Верный Удар" (True Strike)
*   **Цель:** Нельзя увернуться, но урон снижен.
*   **Config:**
    ```json
    {
      "triggers": ["accuracy.true_strike"],
      "raw_mutations": {"physical_damage_mult": "-20%"}
    }
    ```
*   **Trigger (true_strike):**
    ```python
    mutations: {"force.hit_evasion": True}
    ```

### 🔨 "Сокрушение" (Sunder Armor)
*   **Цель:** Игнорирует броню.
*   **Config:**
    ```json
    {
      "pipeline_mutations": {"formula.can_pierce": True}
    }
    ```

### 🩸 "Кровавый Крит" (Bleed on Crit)
*   **Цель:** При крите накладывает кровотечение.
*   **Trigger (ON_CRIT):**
    ```python
    mutations: {
        "formula.crit_damage_boost": True,
        "add_effect": {"id": "bleed"}
    }
    ```

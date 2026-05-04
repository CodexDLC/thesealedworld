# 💾 Schema: Feints (Финты и Приемы)

[⬅️ Назад: Data Schemas](./README.md)

---

## 📋 Обзор
Финты (Feints) — это специальные боевые приемы, которые игрок выбирает вместо обычной атаки.
Они тратят **Тактические Токены** и модифицируют параметры боя (Пайплайн).

---

## ⚙️ 1. Структура Финта (FeintConfigDTO)

```python
class FeintConfigDTO(BaseModel):
    feint_id: str               # Уникальный ID (например, "true_strike")
    name_ru: str                # Название
    description_ru: str         # Описание

    # === Стоимость ===
    cost: FeintCostDTO          # Цена в токенах

    # === Цели ===
    target: TargetType          # SINGLE_ENEMY, ALL_ENEMIES...
    target_count: int = 1       # Количество целей (для мульти-атак)

    # === Модификаторы (Pre-Calc) ===

    # 1. Изменение статов (Строки для калькулятора)
    # Пример: {"physical_damage_mult": "+0.5", "accuracy_mult": "-0.2"}
    raw_mutations: dict[str, str] | None = None

    # 2. Флаги Пайплайна
    # Пример: {"formula.can_pierce": True}
    pipeline_mutations: dict[str, Any] | None = None

    # 3. Активация Триггеров (Правил)
    # Ссылки на ID правил в TRIGGER_RULES
    # Пример: ["accuracy.true_strike", "dodge.counter_on_dodge"]
    triggers: list[str] | None = None

    # === Последствия (Post-Calc) ===

    # Наложение эффектов (при попадании)
    # Пример: [{"id": "blind", "params": {"duration": 2}}]
    effects: list[dict[str, Any]] | None = None
```

---

## ⚙️ 2. Стоимость (FeintCostDTO)

```python
class FeintCostDTO(BaseModel):
    """
    Стоимость в тактических токенах.
    Ключи: "hit", "crit", "block", "parry", "dodge", "tempo".
    Значения: Целые числа (цена).
    """
    tactics: dict[str, int] = {} # Пример: {"hit": 2, "crit": 1}
```

---

## 📝 Примеры JSON

### 1. Верный Удар (True Strike)
Игнорирует уворот, но слабее бьет.
```json
{
  "feint_id": "true_strike",
  "cost": {"tactics": {"hit": 2}},
  "target": "single_enemy",
  "triggers": ["accuracy.true_strike"],
  "raw_mutations": {
    "physical_damage_mult": "-0.2"
  }
}
```

### 2. Бросок Песка (Sand Throw)
Ослепляет врага.
```json
{
  "feint_id": "sand_throw",
  "cost": {"tactics": {"tempo": 3}},
  "target": "single_enemy",
  "raw_mutations": {
    "physical_damage_mult": "-0.8"
  },
  "effects": [
    {
      "id": "blind",
      "params": {"duration": 2}
    }
  ]
}
```

### 3. Рассечение (Cleave)
Атака по 3 целям.
```json
{
  "feint_id": "cleave",
  "cost": {"tactics": {"hit": 2, "crit": 1}},
  "target": "all_enemies",
  "target_count": 3,
  "raw_mutations": {
    "physical_damage_mult": "-0.3"
  }
}
```

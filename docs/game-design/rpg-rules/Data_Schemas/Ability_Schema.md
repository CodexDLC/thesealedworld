# 💾 Schema: Abilities (Способности и Магия)

[⬅️ Назад: Data Schemas](./README.md)

---

## 📋 Обзор
Абилки (Abilities) — это активные действия, получаемые через Дары (Gifts) или Классы.
В отличие от Финтов, они тратят **Энергию (EN)**, **Здоровье (HP)** или **Токены Дара**.

Абилки делятся на два типа:
1.  **Combat (Атакующие):** Проходят через Combat Pipeline (Accuracy -> Crit -> Damage).
2.  **Support (Мирные):** Применяются мгновенно (Heal, Buff, Summon).

---

## ⚙️ 1. Структура Абилки (AbilityConfigDTO)

```python
class AbilityConfigDTO(BaseModel):
    ability_id: str             # Уникальный ID (например, "fireball")
    name_ru: str
    description_ru: str

    # === Стоимость ===
    cost: AbilityCostDTO        # Цена (EN, HP, Gift Tokens)

    # === Цели ===
    target: TargetType          # SINGLE_ENEMY, ALL_ALLIES...
    target_count: int = 1

    # === Режим ===
    is_attack: bool = True      # True = Запускает Pipeline. False = Мгновенный эффект.

    # === PIPELINE CONFIG (Только если is_attack=True) ===

    # 1. Изменение статов (Строки для калькулятора)
    # Пример: {"magical_damage_bonus": "*2.0"}
    raw_mutations: dict[str, str] | None = None

    # 2. Флаги Пайплайна
    # Пример: {"damage.fire": True, "restriction.ignore_block": True}
    pipeline_mutations: dict[str, Any] | None = None

    # 3. Активация Триггеров
    # Пример: ["crit.burn_on_crit"]
    triggers: list[str] | None = None

    # 4. Полная замена урона (фиксированный урон)
    # Пример: [100, 150]
    override_damage: tuple[float, float] | None = None

    # === EFFECTS (Для всех типов) ===

    # Наложение эффектов (Баффы, Дебаффы, Хил)
    # Для Атаки: накладываются при попадании (ON_HIT).
    # Для Саппорта: накладываются сразу.
    # Использует структуру EffectParams.
    # Пример: [{"id": "burn", "params": {"duration": 3, "power": 1.5}}]
    effects: list[dict[str, Any]] | None = None
```

---

## ⚙️ 2. Стоимость (AbilityCostDTO)

```python
class AbilityCostDTO(BaseModel):
    energy: int = 0       # Мана / Энергия
    hp: int = 0           # Здоровье (Кровавая магия)
    gift_tokens: int = 0  # Спец. ресурс Дара
```

---

## 📝 Примеры JSON

### 1. Огненный Шар (Fireball) - Атака
Магическая атака с шансом поджога.
```json
{
  "ability_id": "fireball",
  "is_attack": true,
  "cost": {"energy": 25},
  "target": "single_enemy",

  // Делаем урон Огненным
  "pipeline_mutations": {
    "damage.fire": true
  },

  // Бонус к маг. урону
  "raw_mutations": {
    "magical_damage_bonus": "+20"
  },

  // Триггер поджога при крите
  "triggers": ["crit.burn_on_crit"]
}
```

### 2. Лечение (Heal) - Саппорт
Мгновенное восстановление здоровья.
```json
{
  "ability_id": "heal",
  "is_attack": false,
  "cost": {"energy": 15},
  "target": "single_ally",

  // Эффект лечения
  "effects": [
    {
      "id": "restore_hp",
      "params": {"value": 50}
    }
  ]
}
```

### 3. Каменная Кожа (Stone Skin) - Бафф
Повышает броню.
```json
{
  "ability_id": "stone_skin",
  "is_attack": false,
  "cost": {"energy": 30},
  "target": "self",

  "effects": [
    {
      "id": "buff_armor",
      "params": {
        "duration": 3,
        "mutations": {
          "damage_reduction_flat": 20
        }
      }
    }
  ]
}
```

# ⚡ Modifiers Reference (Справочник Модификаторов)

[⬅️ Назад: RPG Rules](../README.md) | [🏠 Архитектура (Root)](../../../README.md)

---

## 🎯 Описание
Этот документ — единый справочник всех модификаторов (статов) в игре.
Он описывает, как рассчитывается каждый параметр: его базовое значение (от Атрибутов), множители (от Навыков) и внешние источники (Предметы, Баффы).

Структура соответствует DTO (`modifier_dto.py`).

---

## ❤️ Vitals (Жизненные показатели)

### `hp_max` (int)
**Максимальное здоровье.**
- **Источник (Base):** `Endurance` (4 HP/pt).
- **Множитель:** —
- **Источник:** Buffs.

### `hp_regen` (float)
**Регенерация здоровья (ед/ход).**
- **Источник (Base):** `Endurance` (0.5/pt).
- **Множитель:** Навык `Anatomy` (до x2).
- **Источник:** Buffs, Items.

### `energy_max` (int)
**Максимальная энергия (Mana Pool).**
- **Источник (Base):** `Mental` (2 Energy/pt).
- **Множитель:** —
- **Источник:** Buffs, Items.

### `energy_regen` (float)
**Регенерация энергии (ед/ход).**
- **Источник (Base):** `Mental` (0.5/pt).
- **Множитель:** Навык `Anatomy` (до x2).
- **Источник:** Buffs, Items.

### `resource_cost_reduction` (float)
**Снижение стоимости способностей (%).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix, Buffs.

### `initiative` (float)
**Бонус к инициативе (скорости хода).**
- **Источник (Base):** `Agility` (влияние на очередность хода).
- **Множитель:** —
- **Источник:** Item Affix.

---

## ⚔️ Hand Stats (Оружие)

### Main Hand (Правая рука)

#### `main_hand_damage_base`
**Базовый урон.**
- **Источник (Base):** `Strength` (1-2 DMG/pt) для безоружного боя; для оружия Strength идет через глобальный физический бонус.
- **Множитель:** —
- **Источник:** Item (Weapon).

#### `main_hand_damage_spread`
**Разброс урона (0.1 = 10%).**
- **Источник (Base):** —
- **Множитель:** Навык `Weapon Mastery` (сжимает spread).
- **Источник:** Item (Weapon).

#### `main_hand_damage_bonus`
**Дополнительный урон.**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix.

#### `main_hand_armor_penetration_pct`
**Пробивание брони (%).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix.

#### `main_hand_accuracy`
**Точность (%).**
- **Источник (Base):** —
- **Множитель:** Навык `Weapon Mastery` (снимает штраф).
- **Источник:** Item (Weapon).

#### `main_hand_crit_chance`
**Шанс крита (%).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item (Weapon Base + Quality).

### Off Hand (Левая рука / Щит)

#### `off_hand_damage_base`
**Базовый урон левой руки.**
- **Источник (Base):** —
- **Множитель:** Навык `Dual Wielding` (повышает эффективность урона с 50% до 100%).
- **Источник:** Item (Weapon).

#### `off_hand_accuracy`
**Точность левой руки.**
- **Источник (Base):** —
- **Множитель:** Навык `Dual Wielding` (снимает штраф точности).
- **Источник:** Item (Weapon).

---

## 🔮 Physical & Magical (Глобальные)

### Physical

#### `physical_damage`
**Глобальный физический урон от атрибутов.**
- **Источник (Base):** `Strength` (1-2 DMG/pt по дизайну; текущая bridge-формула 1.0/pt).
- **Множитель:** —
- **Источник:** Gifts, passives, buffs.

#### `physical_damage_bonus`
**Глобальный бонус к физ. урону (обе руки).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix, Gifts, Buffs.

#### `physical_accuracy_bonus`
**Глобальный бонус к точности.**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix, Buffs.

### Magical

#### `magical_damage_base`
**Базовый маг. урон.**
- **Источник (Base):** `Intellect` (1-2 DMG/pt).
- **Множитель:** —
- **Источник:** —

#### `magical_damage_spread`
**Разброс маг. урона.**
- **Источник (Base):** —
- **Множитель:** Навык (возможно Spell Mastery).
- **Источник:** Item (Wand/Staff).

#### `magical_damage_bonus`
**Бонус к маг. урону.**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix, Buffs.

#### `magical_penetration`
**Магическое пробивание (Resist Pen, %).**
- **Источник (Base):** `Intellect` (2%/pt).
- **Множитель:** —
- **Источник:** Item Affix.

#### `magical_accuracy`
**Магическая точность (%).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item (Wand/Spell).

#### `magical_damage_power`
**Сила заклинаний (множитель).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix, Buffs.

#### `spell_land_chance`
**Шанс прохождения заклинания (Debuff Accuracy, %).**
- **Источник (Base):** `Projection` (Debuff Efficiency).
- **Множитель:** —
- **Источник:** —

#### `magical_crit_chance`
**Шанс маг. крита (%).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item (Wand/Spell), `Prediction` (возможно).

#### `magical_crit_cap`
**Кап маг. крита (Hard Cap, %).**
- **Источник (Base):** Системный параметр.
- **Множитель:** —
- **Источник:** —

---

## 🛡️ Defensive (Защита)

### Active Avoidance

#### `dodge_chance`
**Шанс уклонения (%).**
- **Источник (Base):** `Agility` (+5%/pt).
- **Множитель:** Навык `Two-Handed` (снижает штраф к увороту от тяжелого оружия).
- **Источник:** Item Affix.

#### `dodge_cap`
**Максимальный шанс уклонения (Hard Cap, %).**
- **Источник (Base):** Системный параметр.
- **Множитель:** —
- **Источник:** Item (Dodge Cap Mod).

#### `anti_dodge_chance`
**Снижение уклонения врага (Hit Rate, %).**
- **Источник (Base):** `Perception` (+3%/pt) — Трейсинг целей.
- **Множитель:** —
- **Источник:** Item Affix.

#### `parry_chance`
**Шанс парирования оружием (%).**
- **Источник (Base):** —
- **Множитель:** `skill_parrying` применяется в `CombatResolver`.
- **Источник:** Item (Weapon).

#### `parry_cap`
**Кап парирования (Hard Cap, %).**
- **Источник (Base):** Системный параметр.
- **Множитель:** —
- **Источник:** —

#### `shield_block_chance`
**Шанс блока щитом (%).**
- **Источник (Base):** —
- **Множитель:** `skill_parrying` применяется в `CombatResolver`; `Shield Mastery` отвечает за отдельные механики щитовика.
- **Источник:** Item (Shield).

#### `shield_block_cap`
**Кап блока (Hard Cap, %).**
- **Источник (Base):** Системный параметр.
- **Множитель:** —
- **Источник:** —

### Mitigation (Damage Reduction)

#### `physical_resistance`
**Сопротивление физ. урону (%).**
- **Источник (Base):** `Endurance` (2%/pt).
- **Множитель:** —
- **Источник:** Item Affix.

#### `magical_resistance`
**Сопротивление магии (%).**
- **Источник (Base):** `Mental` (2%/pt) — Energy-Resistance.
- **Множитель:** —
- **Источник:** Item Affix.

#### `resistance_cap`
**Кап резистов (Hard Cap, %).**
- **Источник (Base):** Системный параметр.
- **Множитель:** —
- **Источник:** —

#### `damage_reduction_flat`
**Плоское снижение урона (Armor).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item (Armor Power).

---

## 🔥 Elemental & Status (Стихии и Статусы)

### Elemental (Energy-Resistances)
**Стихии:** Fire, Water, Air, Earth, Light, Dark, Arcane, Nature.

#### `{element}_damage_bonus`
**Бонус к урону стихией (%).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix, Ability.

#### `{element}_resistance`
**Сопротивление стихии (%).**
- **Источник (Base):** `Mental` (2%/pt) — Energy-Resistance.
- **Множитель:** Навык `Adaptation` (до x3).
- **Источник:** Item Affix.

### Control (Mental Base)

#### `control_chance_bonus`
**Шанс наложить контроль (Stun, Root, %).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix, Ability.

#### `control_resistance`
**Сопротивление контролю (%).**
- **Источник (Base):** `Mental` (2%/pt) — Control-Resistance.
- **Множитель:** Навык `Adaptation` (до x3).
- **Источник:** Item Affix.

#### `mental_resistance`
**Сопротивление ментальным атакам (Fear, Sleep, %).**
- **Источник (Base):** `Mental` (2%/pt) — Control-Resistance.
- **Множитель:** Навык `Adaptation` (до x3).
- **Источник:** —

#### `debuff_avoidance`
**Шанс избежать наложения дебаффа (%).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix, Buffs.

#### `shock_resistance`
**Сопротивление шоку (%).**
- **Источник (Base):** `Mental` (2%/pt) — Energy-Resistance.
- **Множитель:** —
- **Источник:** —

### Bio (Endurance Base)

#### `poison_damage_bonus`
**Урон ядом (flat/%).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix, Ability.

#### `poison_resistance`
**Сопротивление яду (%).**
- **Источник (Base):** `Endurance` (2%/pt) — Bio-Resistance.
- **Множитель:** Навык `Adaptation` (до x3).
- **Источник:** Item Affix.

#### `poison_efficiency`
**Эффективность ядов (Land Chance, %).**
- **Источник (Base):** `Projection` (Debuff Efficiency).
- **Множитель:** Навык `Alchemy`.
- **Источник:** —

#### `bleed_damage_bonus`
**Урон кровотечением (flat).**
- **Источник (Base):** `Strength` (Physical Penetration — глубина раны).
- **Множитель:** Навык `Weapon Mastery`.
- **Источник:** —

#### `bleed_resistance`
**Сопротивление кровотечению (%).**
- **Источник (Base):** `Endurance` (2%/pt) — Bio-Resistance.
- **Множитель:** Навык `Adaptation` (до x3).
- **Источник:** —

---

## ✨ Special Modifiers

### Counter-Attack

#### `counter_attack_chance`
**Шанс контратаки (%).**
- **Источник (Base):** `Memory` (~0.25%/pt) + `Prediction` (~0.15%/pt).
- **Множитель:** Навык `Tactics` (до x5).
- **Источник:** —

#### `counter_attack_cap`
**Кап контратаки (Hard Cap, %).**
- **Источник (Base):** Системный параметр.
- **Множитель:** —
- **Источник:** —

### Vampiric

#### `vampiric_power`
**Сила вампиризма (% от урона в HP).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Gift (Дар), Item Affix.

#### `vampiric_trigger_chance`
**Шанс срабатывания вампиризма (%).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Gift (Дар), Item Affix.

#### `vampiric_trigger_cap`
**Кап шанса (Hard Cap, %).**
- **Источник (Base):** Системный параметр.
- **Множитель:** —
- **Источник:** —

### Healing & Pets

#### `healing_power`
**Сила исходящего исцеления (множитель).**
- **Источник (Base):** —
- **Множитель:** Навык `First Aid`.
- **Источник:** —

#### `received_healing_bonus`
**Бонус к входящему исцелению (множитель).**
- **Источник (Base):** —
- **Множитель:** Навык `Anatomy`.
- **Источник:** —

#### `pet_efficiency_mult`
**Множитель эффективности питомца (HP, DMG, etc).**
- **Источник (Base):** —
- **Множитель:** Навык `Taming`.
- **Источник:** —

### Misc

#### `damage_mult`
**Глобальный множитель исходящего урона.**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Buff, Gift.

#### `thorns_damage_flat`
**Урон шипами (возврат урона, flat).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item Affix, Buff.

#### `environment_{type}_resistance`
**Защита от среды (Cold, Heat, Gravity, Bio).**
- **Источник (Base):** `Endurance` (2%/pt).
- **Множитель:** —
- **Источник:** Item (Armor, Hazmat).

---

## 💰 Economy & World

#### `trade_discount`
**Скидка у торговцев (%).**
- **Источник (Base):** `Projection` (Social Influence).
- **Множитель:** —
- **Источник:** Item Affix, Buffs.

#### `find_loot_chance`
**Шанс найти лучший лут (%).**
- **Источник (Base):** `Prediction` (Loot Luck) + `Perception` (Detection).
- **Множитель:** —
- **Источник:** Item Affix.

#### `crafting_success_chance`
**Шанс успеха крафта (%).**
- **Источник (Base):** —
- **Множитель:** Навык `Crafting`.
- **Источник:** —

#### `crafting_critical_chance`
**Шанс крит. успеха крафта (%).**
- **Источник (Base):** `Prediction` (Crafting Quality).
- **Множитель:** Навык `Crafting`.
- **Источник:** —

#### `crafting_speed`
**Скорость крафта (множитель).**
- **Источник (Base):** —
- **Множитель:** Навык `Crafting`.
- **Источник:** —

#### `skill_gain_bonus`
**Скорость прокачки навыков (%).**
- **Источник (Base):** `Memory` (XP Gain — глобальный множитель опыта).
- **Множитель:** —
- **Источник:** Item Affix, Buffs.

#### `inventory_slots_bonus`
**Доп. слоты инвентаря (int).**
- **Источник (Base):** —
- **Множитель:** —
- **Источник:** Item (Backpack), Buff.

#### `weight_limit_bonus`
**Доп. переносимый вес (int).**
- **Источник (Base):** `Strength` (Carry Weight).
- **Множитель:** —
- **Источник:** Item (Backpack).

#### `xp_multiplier`
**Множитель опыта (float).**
- **Источник (Base):** `Memory` (XP Gain).
- **Множитель:** —
- **Источник:** Item Affix, Buffs.

---

## 🎓 Secondary Skills (Skills as Modifiers)

#### `skill_crafting`
**Навык крафта (float, 0.0-1.0).**
- **Множитель:** Практика крафта (XP Factor).

#### `skill_trading`
**Навык торговли (float, 0.0-1.0).**
- **Множитель:** Практика торговли (XP Factor).

#### `skill_gathering`
**Навык сбора ресурсов (float, 0.0-1.0).**
- **Источник (Base):** Зависит от типа сбора (Mining, Skinning, etc).
- **Множитель:** Практика сбора (XP Factor).

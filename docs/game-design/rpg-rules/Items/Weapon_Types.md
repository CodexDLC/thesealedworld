# ⚔️ Weapon Types & Triggers (Типы Оружия)

[⬅️ Назад: Items Rules](./README.md) | [🏠 Архитектура (Root)](../../../README.md)

---

## 🎯 Описание
Справочник по типам оружия. Каждое оружие имеет уникальный стиль игры, определяемый его **Триггерами** (спецэффектами при крите/ударе).

Runtime хранит триггеры на предметах как `section.trigger_id`, например `crit.bleed_on_crit`.
В каталоге правил сами id лежат без секции (`bleed_on_crit`), а секция выбирает событие пайплайна.

---

## 🗡️ Swords (Мечи)
**Философия:** «Баланс и мастерство». Универсальное оружие.
**Атрибуты:** `STR (2) + AGI (1) + DEX (1)`.

### Типы и Триггеры
*   **Longsword (Длинный меч):**
    *   **Trigger:** `crit.bleed_on_crit` (On Crit).
    *   **Эффект:** Накладывает кровотечение (DoT).
*   **Greatsword (Двуручный меч):**
    *   **Trigger:** `crit.heavy_strike_on_crit` / planned `crit.cleave_on_crit` (On Crit).
    *   **Эффект:** Урон по соседней цели (AoE).
*   **Katana (Катана):**
    *   **Trigger:** `crit.bleed_on_crit` (On Crit).
    *   **Эффект:** Усиленное кровотечение или мгновенный урон от стаков (Hemorrhage).
*   **Scimitar (Сабля):**
    *   **Trigger:** planned `damage.flow_on_hit` (On Hit).
    *   **Эффект:** Накапливает инициативу/скорость с каждым ударом.

---

## 🔨 Macing (Дробящее)
**Философия:** «Неотвратимая сила». Контроль и разрушение брони.
**Атрибуты:** `STR (3) + CON (1)`.

### Типы и Триггеры
*   **Mace (Булава):**
    *   **Trigger:** `crit.stun_on_crit` (On Crit).
    *   **Эффект:** Оглушение (Stun) на 1 ход.
*   **War Hammer (Боевой молот):**
    *   **Trigger:** `crit.stun_on_crit` / planned `crit.armor_crush_on_crit` (On Crit).
    *   **Эффект:** Перманентное снижение брони цели.
*   **Flail (Кистень):**
    *   **Trigger:** `crit.unblockable_crit` or planned `damage.shield_bypass_on_hit`.
    *   **Эффект:** Игнорирует блок щитом.
*   **Maul (Тяжёлый молот):**
    *   **Trigger:** `crit.heavy_strike_on_crit` / planned `damage.concussion_on_hit`.
    *   **Эффект:** Сжигает энергию/выносливость цели.

---

## 🏹 Archery (Стрелковое)
**Философия:** «Проекция смерти». Дистанция и высокий разовый урон.
**Атрибуты:** `AGI (2) + PER (1) + STR (1)`.

### Типы и Триггеры
*   **Shortbow (Короткий лук):**
    *   **Trigger:** `control.evasive_shot` (On Hit).
    *   **Эффект:** Бафф на уклонение после выстрела.
*   **Longbow (Длинный лук):**
    *   **Trigger:** `crit.heavy_strike_on_crit` (On Crit).
    *   **Эффект:** Множитель крита **x3.0**.
*   **Composite Bow (Композитный лук):**
    *   **Trigger:** `crit.stun_on_crit` / planned `crit.heavy_impact_on_crit` (On Crit).
    *   **Эффект:** Отбрасывание (Knockback) и Стан.
*   **Heavy Crossbow (Тяжёлый арбалет):**
    *   **Trigger:** `crit.piercing_crit` / planned `damage.armor_pierce_on_hit`.
    *   **Эффект:** Игнорирует 100% брони.

---

## 🔱 Polearms (Древковое)
**Философия:** «Контроль дистанции». Reach и AoE.
**Атрибуты:** `STR (2) + AGI (1) + CON (1)`.

### Типы и Триггеры
*   **Spear (Копье):**
    *   **Trigger:** planned `damage.keep_distance_on_hit`.
    *   **Эффект:** Замедление врага (Slow).
*   **Pike (Пика):**
    *   **Trigger:** `crit.piercing_crit` (On Crit).
    *   **Эффект:** Игнорирует Резисты и Броню.
*   **Halberd (Алебарда):**
    *   **Trigger:** `crit.heavy_strike_on_crit` (On Crit).
    *   **Эффект:** Множитель крита **x3.0**.
*   **Trident (Трезубец):**
    *   **Trigger:** planned `damage.entangle_on_hit` / `parry.disarm_on_parry`.
    *   **Эффект:** Обездвиживание (Root) или Обезоруживание.

---

## 🤺 Fencing (Фехтование)
**Философия:** «Ping 0ms». Скорость, точность, уколы.
**Атрибуты:** `AGI (2) + PER (1) + STR (1)`.

### Типы и Триггеры
*   **Stiletto (Стилет):**
    *   **Trigger:** `crit.piercing_crit` (On Crit).
    *   **Эффект:** Игнорирует Flat Armor.
*   **Rapier (Рапира):**
    *   **Trigger:** `crit.true_crit` / planned `crit.vitals_trace_on_crit` (On Crit).
    *   **Эффект:** Игнорирует % Resistance.
*   **Main-gauche (Дага):**
    *   **Trigger:** `parry.counter_on_parry` (On Parry).
    *   **Эффект:** Контратака с бонусом урона.
*   **Katar (Катар):**
    *   **Trigger:** planned `crit.vitals_strike_on_crit` (On Crit).
    *   **Эффект:** True Damage (Чистый урон).

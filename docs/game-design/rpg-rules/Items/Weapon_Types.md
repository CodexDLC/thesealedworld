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

### Типовые base items
| Item | Runtime trigger | Роль |
|---|---|---|
| `sword` / Меч | `crit.bleed_on_crit` | Базовый одноручный меч: баланс урона, точности и парирования. |
| `longsword` / Длинный меч | `crit.bleed_on_crit` | Более стабильный клинок с усиленным parry-профилем. |
| `greatsword` / Двуручный меч | `crit.heavy_strike_on_crit` | Медленный двуручник с высоким base power и сильным критом. |

### Уникальные base items
| Item | Runtime trigger | Поведение |
|---|---|---|
| `katana` / Катана | `crit.bleed_on_crit` | Быстрый двуручный клинок: высокий trigger chance и `bleed_damage_bonus`. |
| `scimitar` / Сабля | `crit.true_crit` | Темповый одноручный клинок: точный крит, меньше raw power. |

### Planned triggers
| Trigger | Предлагаемая реализация |
|---|---|
| `crit.cleave_on_crit` | На критическом ударе создать вторичный damage event по соседней цели с 40-60% урона основного удара. |
| `damage.flow_on_hit` | При успешном попадании дать атакующему tempo-token или короткий `buff_accuracy`; не должен напрямую повышать base damage. |

---

## 🔨 Macing (Дробящее)
**Философия:** «Неотвратимая сила». Контроль и разрушение брони.
**Атрибуты:** `STR (3) + CON (1)`.

### Типовые base items
| Item | Runtime trigger | Роль |
|---|---|---|
| `hatchet` / Топорик | `crit.heavy_strike_on_crit` | Легкое рубящее оружие с высоким разбросом и небольшой пробивной силой. |
| `battle_axe` / Боевой топор | `crit.heavy_strike_on_crit` | Агрессивный одноручный топор: больше penetration, выше accuracy penalty. |
| `mace` / Булава | `crit.stun_on_crit` | Базовая дробящая ветка: контроль через stun. |

### Уникальные base items
| Item | Runtime trigger | Поведение |
|---|---|---|
| `warhammer` / Боевой молот | `crit.stun_on_crit` | Двуручный anti-armor профиль: высокий power, penetration, evasion penalty. |
| `flail` / Кистень | `crit.unblockable_crit` | Цепное оружие против щитов: крит игнорирует block. |

### Planned triggers
| Trigger | Предлагаемая реализация |
|---|---|
| `crit.armor_crush_on_crit` | На критическом ударе накладывать `debuff_armor` или отдельный stackable armor-break effect. |
| `damage.concussion_on_hit` | При попадании снижать концентрацию/энергию цели, когда EN runtime станет боевым ресурсом. |

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

### Типовые base items
| Item | Runtime trigger | Роль |
|---|---|---|
| `spear` / Копье | `crit.piercing_crit` | Одноручное reach-оружие: работает со щитом, умеренная пробивная сила. |
| `pike` / Пика | `crit.piercing_crit` | Двуручный длинный укол: сильный penetration, хуже мобильность. |
| `halberd` / Алебарда | `crit.heavy_strike_on_crit` | Двуручный рубящий polearm: высокий power и тяжелый крит. |

### Уникальные base items
| Item | Runtime trigger | Поведение |
|---|---|---|
| `quarterstaff` / Боевой посох | `crit.stun_on_crit` | Оборонительный двуручный посох: высокий parry, низкий kill pressure. |
| `trident` / Трезубец | `control.knockdown_on_hit` | Контрольный polearm: попадание может сбить цель с ног. |

### Planned triggers
| Trigger | Предлагаемая реализация |
|---|---|
| `damage.keep_distance_on_hit` | При попадании наложить short slow/accuracy penalty на цель или дать defender-disengage token. |
| `damage.entangle_on_hit` | При попадании наложить root-like control effect, запрещающий dodge/reposition, но не полный stun. |

---

## 🤺 Fencing (Фехтование)
**Философия:** «Ping 0ms». Скорость, точность, уколы.
**Атрибуты:** `AGI (2) + PER (1) + STR (1)`.
**Parry-баланс:** main-hand-only клинок дает примерно в 2 раза меньшую базу парирования, чем специализированный off-hand парирующий клинок. Off-hand оружие платит за защиту более слабым атакующим профилем.

### Типовые base items
| Item | Runtime trigger | Роль |
|---|---|---|
| `knife` / Нож | `control.bleed_on_hit` | Самый легкий клинок; main hand и off hand. |
| `dagger` / Кинжал | `crit.bleed_on_crit` | Базовый быстрый кинжал; main hand и off hand. |
| `stiletto` / Стилет | `crit.piercing_crit` | Узкий пробивающий кинжал; main hand и off hand. |

### Уникальные base items
| Item | Runtime trigger | Поведение |
|---|---|---|
| `rapier` / Рапира | `crit.true_crit` | Main-hand дуэльное оружие: точность, parry, reliable crit. |
| `main_gauche` / Дага | `parry.counter_on_parry` | Off-hand парирующий клинок: высокий parry и riposte, но ниже raw power, чем у основных кинжалов. |
| `katar` / Катар | `crit.piercing_crit` | Близкий агрессивный клинок: высокий crit chance, ниже parry. |

### Planned triggers
| Trigger | Предлагаемая реализация |
|---|---|
| `crit.vitals_trace_on_crit` | На критическом ударе временно снижать evasion/dodge cap цели или ставить vulnerability marker. |
| `crit.vitals_strike_on_crit` | На критическом ударе часть урона проводить как true damage через armor/resist caps. |

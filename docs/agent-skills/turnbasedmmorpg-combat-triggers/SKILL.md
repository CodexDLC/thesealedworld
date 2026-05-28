# turnbasedmmorpg-combat-triggers SKILL

Читай этот файл перед любой работой с combat triggers: добавлением нового триггера, weapon trigger, изменением log_builder, event_texts, или merge правил.

---

## Что такое trigger в этом проекте

Trigger — пассивное правило боя, которое срабатывает в определённый момент размена (ON_CRIT, ON_DODGE, ON_PARRY, и т.д.). В отличие от финтов (активный выбор игрока), триггеры активируются автоматически, если установлен соответствующий флаг в `TriggerRulesFlagsDTO`.

Крит в игре — это **не всегда x2 урон**. Крит может быть триггером, который накладывает bleed, stun, pierce, или даёт тройной урон. Это определяется набором активных trigger flags в `CritTriggersDTO`.

---

## Структура данных (паттерн — как feints)

### TriggerTechnicalDTO
Чистая логика. Читается только resolver-ом и log_builder-ом.

```python
class TriggerTechnicalDTO(BaseModel):
    trigger_id: str                               # e.g. "bleed_on_crit"
    event: str                                    # "ON_CRIT", "ON_MISS", "ON_DODGE", etc.
    chance: float = 1.0                           # вероятность срабатывания [0.0–1.0]
    mutations: dict[str, Any]                     # мутации контекста/результата
    applied_effect_ids: list[str]                 # явный список эффектов (для log_builder)
    token_grants_attacker: list[str]              # токены атакующему при срабатывании
    token_grants_defender: list[str]              # токены защищающемуся при срабатывании
```

`applied_effect_ids` заполняется **вручную** при определении триггера — не выводится из `mutations`. Позволяет log_builder-у разрешить имя эффекта без парсинга мутаций.

### TriggerCatalogEntryDTO
Полная каталожная запись (аналог FeintCatalogEntryDTO).

```python
class TriggerCatalogEntryDTO(CombatCatalogEntryDTO):
    key: str                      # "combat.trigger.crit.bleed_on_crit"
    technical: TriggerTechnicalDTO
    descriptive: CombatDescriptionDTO
```

### CombatDescriptionDTO
Стандартный класс из `common/descriptions.py`. Разбит по taxonomy (humanoid / beast). Пока реализуется только humanoid; beast_event_texts передаётся через `default_trigger_proc_event_texts()`.

---

## Catalog key convention

```
combat.trigger.{group}.{trigger_id}
```

| Group | Resolver stage / смысл | Примеры |
|---|---|---|
| `crit` | ON_CRIT | `combat.trigger.crit.bleed_on_crit` |
| `miss` | ON_MISS | `combat.trigger.miss.rage_on_miss` |
| `accuracy` | ON_ACCURACY_CHECK | `combat.trigger.accuracy.true_strike` |
| `dodge` | ON_DODGE | `combat.trigger.dodge.counter_on_dodge` |
| `parry` | ON_PARRY | `combat.trigger.parry.counter_on_parry` |
| `block` | ON_BLOCK | `combat.trigger.block.bash_on_block` |
| `control` | ON_CHECK_CONTROL | `combat.trigger.control.stun_on_hit` |
| `damage` | ON_DAMAGE | `combat.trigger.damage.execute_low_hp` |
| `style` | Любое событие (стиль боя) | `combat.trigger.style.offhand_attack` |
| `weapon` | Оружейный триггер | `combat.trigger.weapon.katana_bleed` |

**Важно:** `trigger_id` в `TriggerTechnicalDTO` — это имя флага в `TriggerRulesFlagsDTO` (например, `style_dual_extra`). Catalog key использует семантическое имя (например, `style.offhand_attack`). Они могут отличаться.

---

## event_texts для триггеров

`CombatEventTextSetDTO` имеет специальные поля для триггеров (в дополнение к стандартным `use`, `hit`, `crit`, etc.):

| Поле | Когда используется |
|---|---|
| `proc` | Generic fallback — любое срабатывание |
| `hit_proc` | Trigger сработал при попадании (ON_HIT / ON_CHECK_CONTROL) |
| `crit_proc` | Trigger сработал на крите (ON_CRIT) |
| `miss_proc` | Trigger сработал при промахе (ON_MISS) |
| `dodge_proc` | Trigger сработал при уклонении (ON_DODGE) |
| `parry_proc` | Trigger сработал при парировании (ON_PARRY) |
| `block_proc` | Trigger сработал при блоке (ON_BLOCK) |
| `apply_effect` | Стандартное поле — наложение эффекта |
| `token_gain` | Получение токена от триггера |
| `counter` | Контратака активирована |
| `extra_strike` | Дополнительный удар |

**Порядок разрешения в log_builder:** `{event}_proc` → `proc` → `{event}` (fallback на стандартное поле).

Переменные шаблонов: `{source}`, `{target}`, `{trigger}` (display_name), `{effect}`, `{damage}`, `{token}`.

Используй `default_trigger_proc_event_texts(name)` из `common/descriptions.py` для beast_event_texts или как заглушку.

---

## Merge rules (когда триггер отдельная строка)

| Тип триггера | Примеры | Отдельная строка лога? |
|---|---|---|
| Effect applicator | `bleed_on_crit`, `stun_on_crit`, `stun_on_hit`, `bleed_on_hit` | **Нет** — вплетается в summary |
| Tactical pipeline flag | `true_crit`, `piercing_crit`, `unblockable_crit`, `heavy_strike_on_crit` | **Нет** |
| Token grant | `rage_on_miss` | **Нет** — видно через badge |
| Accuracy / evasion override | `true_strike`, `style_ranged_perfect_backstep`, `style_2h_ignore` | **Нет** |
| Counter-attack | `counter_on_parry`, `counter_on_dodge` | **Да** — генерирует собственный обмен |
| Extra strike | `style_dual_extra`, `bash_on_block` | **Да** — собственный обмен и damage |

Новые триггеры типа counter / extra_strike добавлять в `_SEPARATE_LINE_TRIGGERS` в `log_builder.py`.

---

## Weapon triggers

Weapon trigger — обычный `TriggerCatalogEntryDTO` с group `weapon`. Оружие ссылается на него через `BaseItemDTO.triggers: list[str]` (список `trigger_id`).

### Файл определений
`src/backend/features/game_catalog/combat/resources/triggers/definitions/rules/weapon_triggers.py`
Экспортирует `WEAPON_TRIGGER_CATALOG: list[TriggerCatalogEntryDTO]`.
Добавляется в `ALL_TRIGGER_CATALOG_ENTRIES` в `definitions/catalog.py`.

### Пример weapon trigger
```python
TriggerCatalogEntryDTO(
    key="combat.trigger.weapon.katana_bleed",
    technical=TriggerTechnicalDTO(
        trigger_id="katana_bleed",
        event="ON_CRIT",
        chance=0.75,
        mutations={"add_effect": {"id": "dot_bleed"}},
        applied_effect_ids=["dot_bleed"],
    ),
    descriptive=build_combat_description(
        resource_type="trigger",
        resource_id="katana_bleed",
        display_name="Кровь катаны",
        short_description="Критический удар катаной открывает кровотечение.",
        humanoid_event_texts=CombatEventTextSetDTO(
            crit_proc=["{source} рассекает {target} катаной; лезвие вскрывает вену."],
            apply_effect=["{source} накладывает {effect} на {target}."],
        ),
        beast_event_texts=default_trigger_proc_event_texts("Кровь катаны"),
    ),
)
```

### Привязка к оружию
В файле определения оружия (например, `swords/katana.py`):
```python
BaseItemDTO(
    ...
    triggers=["katana_bleed"],  # trigger_id из TriggerTechnicalDTO
)
```

---

## Как добавить новый триггер

1. **Определить group** — по resolver stage (`crit`, `parry`, `dodge`, etc.) или `weapon`/`style`
2. **Создать запись** в нужном `definitions/rules/on_*.py` или `weapon_triggers.py`:
   - `TriggerTechnicalDTO` с `trigger_id`, `event`, `chance`, `mutations`, `applied_effect_ids`
   - `build_combat_description(...)` с `humanoid_event_texts` по нужному `{event}_proc` или `proc`
   - Обернуть в `TriggerCatalogEntryDTO(key="combat.trigger.{group}.{trigger_id}", ...)`
3. **Добавить в `*_CATALOG`** соответствующего файла правил
4. **Добавить bool флаг** в нужный `*TriggersDTO` в `trigger_rules.py`:
   ```python
   class CritTriggersDTO(BaseModel):
       bleed_on_crit: bool = False
       my_new_trigger: bool = False   # добавить сюда
   ```
5. **Если weapon trigger** — добавить `trigger_id` в `triggers: list[str]` оружия в `BaseItemDTO`
6. **Если counter / extra_strike** — добавить `trigger_id` в `_SEPARATE_LINE_TRIGGERS` в `log_builder.py`

---

## Ключевые файлы

| Файл | Назначение |
|---|---|
| `src/backend/features/game_catalog/combat/resources/triggers/schemas.py` | TriggerTechnicalDTO, TriggerCatalogEntryDTO |
| `src/backend/features/game_catalog/combat/resources/common/descriptions.py` | CombatEventTextSetDTO (включая proc-поля), default_trigger_proc_event_texts |
| `src/backend/features/game_catalog/combat/resources/triggers/__init__.py` | Реестр: TRIGGER_REGISTRY, TRIGGER_CATALOG_BY_KEY, public API |
| `src/backend/features/game_catalog/combat/resources/triggers/definitions/catalog.py` | ALL_TRIGGER_CATALOG_ENTRIES (агрегатор) |
| `src/backend/features/game_catalog/combat/resources/triggers/definitions/rules/` | Определения по событиям: on_crit.py, on_parry.py, styles.py, weapon_triggers.py, ... |
| `src/backend/features/combat/dto/trigger_rules.py` | TriggerRulesFlagsDTO (bool флаги по stages) |
| `src/backend/features/combat/runtime/engine/resolver.py` | _resolve_triggers() — пишет в res.fired_triggers |
| `src/backend/features/combat/dto/pipeline.py` | InteractionResultDTO.fired_triggers |
| `src/backend/features/combat/integrations/catalog_integrator.py` | CombatCatalogIntegrator — get_trigger_catalog_entry, get_trigger_catalog_entry_by_key |
| `src/backend/features/combat/runtime/services/log_builder.py` | _build_trigger_proc_entry, _trigger_suffix_text, _should_merge_trigger |

---

## Не делать

- Не создавать отдельную папку `descriptions/` — descriptive данные живут рядом с triggers
- Не дублировать damage строку если trigger merge=True
- Не использовать старый `TriggerDTO` — он заменён `TriggerTechnicalDTO`
- Не выводить `applied_effect_ids` из `mutations` — заполнять явно при определении
- Не добавлять `trigger_id` в catalog_key (только в `TriggerTechnicalDTO.trigger_id`)

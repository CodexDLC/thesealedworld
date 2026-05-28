# Skill Catalog Reference

Status: reviewed against current skill definition resources.

Code source:

```text
src/backend/features/game_catalog/skills/resources/definitions/
```

## Catalog Shape

Runtime skill definitions are grouped by:

- `category`: `combat` or `non_combat`;
- `group`: `combat`, `world`, `crafting`, or `social`;
- `ui_group`: player-facing section inside a group;
- `stat_weights`: attribute weights used by progression;
- `rate_mod` and `wall_mod`: progression tuning.

Skill values are normalized floats. Player UI may show them as `0..100`.

## Combat Skills

| Skill key | Player name | UI group | Weights |
| --- | --- | --- | --- |
| `skill_swords` | Владение мечами | weapon mastery | `strength 2`, `agility 1`, `endurance 1` |
| `skill_fencing` | Фехтование | weapon mastery | `agility 2`, `perception 1`, `strength 1` |
| `skill_polearms` | Древковое оружие | weapon mastery | `strength 2`, `agility 1`, `perception 1` |
| `skill_macing` | Дробящее оружие | weapon mastery | `strength 2`, `endurance 1`, `mental 1` |
| `skill_archery` | Стрельба из лука | weapon mastery | `agility 2`, `perception 1`, `strength 1` |
| `skill_unarmed` | Рукопашный бой | weapon mastery | `agility 2`, `strength 1`, `endurance 1` |
| `skill_ranged_combat` | Дальний бой | tactical | `agility 1`, `memory 1`, `perception 1`, `prediction 1` |
| `skill_two_handed` | Двуручный стиль | tactical | `strength 2`, `endurance 1`, `agility 1` |
| `skill_shield_mastery` | Владение щитом | tactical | `strength 2`, `endurance 1`, `agility 1` |
| `skill_dual_wield` | Бой двумя руками | tactical | `agility 2`, `perception 1`, `strength 1` |
| `skill_light_armor` | Легкая броня | armor | `agility 2`, `endurance 1`, `perception 1` |
| `skill_medium_armor` | Средняя броня | armor | `endurance 2`, `strength 1`, `agility 1` |
| `skill_heavy_armor` | Тяжелая броня | armor | `strength 2`, `endurance 2` |
| `skill_parrying` | Парирование | combat support | `agility 2`, `perception 1`, `strength 1` |
| `skill_anatomy` | Анатомия | combat support | `intellect 2`, `perception 2` |
| `skill_tactics` | Тактика | combat support | `intellect 2`, `memory 2` |

## Crafting Skills

| Skill key | Player name | Weights | Rate/wall |
| --- | --- | --- | --- |
| `skill_first_aid` | Первая помощь | `memory 2`, `intellect 1`, `agility 1` | `1.0 / 1.0` |
| `skill_alchemy` | Алхимия | `intellect 2`, `memory 1`, `prediction 1` | `1.5 / 1.0` |
| `skill_weapon_craft` | Оружейное дело | `strength 2`, `agility 1`, `perception 1` | `2.0 / 1.0` |
| `skill_armor_craft` | Бронное дело | `strength 2`, `endurance 2` | `2.0 / 1.0` |
| `skill_jewelry_craft` | Ювелирное дело | `agility 2`, `perception 1`, `prediction 1` | `2.0 / 1.0` |
| `skill_engineering` | Инженерия | `intellect 2`, `agility 1`, `perception 1` | `2.0 / 1.0` |
| `skill_artifact_craft` | Создание артефактов | `mental 2`, `intellect 1`, `memory 1` | `2.5 / 1.5` |

## World Skills

| Skill key | Player name | UI group | Weights |
| --- | --- | --- | --- |
| `skill_mining` | Горное дело | gathering | `strength 2`, `endurance 2` |
| `skill_herbalism` | Травничество | gathering | `perception 2`, `memory 1`, `intellect 1` |
| `skill_skinning` | Снятие шкур | gathering | `agility 2`, `perception 1`, `endurance 1` |
| `skill_woodcutting` | Лесорубство | gathering | `strength 2`, `endurance 2` |
| `skill_hunting` | Охота | gathering | `perception 2`, `agility 1`, `endurance 1` |
| `skill_archaeology` | Археология | gathering | `perception 2`, `memory 1`, `intellect 1` |
| `skill_taming` | Приручение | survival | `projection 2`, `memory 1`, `mental 1` |
| `skill_adaptation` | Адаптация | survival | `endurance 2`, `mental 2` |
| `skill_scouting` | Выслеживание | survival | `perception 2`, `memory 1`, `agility 1` |
| `skill_pathfinder` | Навигация | survival | `perception 2`, `endurance 1`, `agility 1` |

## Social Skills

| Skill key | Player name | UI group | Weights |
| --- | --- | --- | --- |
| `skill_accounting` | Бухгалтерия | trade | `intellect 2`, `prediction 2` |
| `skill_brokerage` | Посредничество | trade | `projection 2`, `prediction 1`, `intellect 1` |
| `skill_contracts` | Договоры | trade | `intellect 2`, `projection 1`, `prediction 1` |
| `skill_trade_relations` | Торговые связи | trade | `projection 2`, `prediction 2` |
| `skill_leadership` | Лидерство | leadership | `projection 2`, `mental 1`, `memory 1` |
| `skill_organization` | Организация | leadership | `intellect 2`, `projection 1`, `memory 1` |
| `skill_team_spirit` | Командный дух | leadership | `projection 2`, `mental 1`, `prediction 1` |
| `skill_egoism` | Эгоизм | leadership | `mental 2`, `prediction 2` |

## Design Notes

The old "sum 4" rule still matches current definitions and remains the design
constraint for skill attribute weights.

Some skill descriptions already include future mechanics. Treat descriptions as
catalog copy plus design intent, not proof that every effect is implemented in
combat runtime.

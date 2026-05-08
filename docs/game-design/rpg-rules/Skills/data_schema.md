# 💾 Skills Data Schema

[⬅️ Назад: Skills Index](./README.md)

## 1. Структура DTO
Все навыки описываются единой моделью `SkillDTO`:

```python
class SkillDTO(BaseModel):
    skill_key: str              # "skill_swords"
    category: SkillCategory     # COMBAT / NON_COMBAT
    group: SkillGroup           # combat / world / crafting / social (storage/domain)
    ui_group: SkillUiGroup      # weapon_mastery / tactical / armor / gathering ...

    # Математика прогрессии
    stat_weights: dict[str, int] # {"strength": 2, "agility": 1}
    rate_mod: float             # Множитель скорости
    wall_mod: float             # Множитель сложности
```

## 2. Интеграция
Навыки используются как коэффициенты в формулах `CombatResolver`.
*   `skill_val` (0-100) преобразуется в множитель (например, `1.0 + val/100`).

## 3. Registry
Доступ через `SKILL_REGISTRY` (O(1) lookup).

## 4. Единый контракт ключей

Все ключи навыков используют префикс `skill_`. Для хранения и runtime-фильтрации каталог делится на четыре группы:

- `combat`: Weapon Mastery, Tactical Styles, Armor Skills, Combat Support.
- `world`: Gathering и Survival.
- `crafting`: First Aid и производственные профессии.
- `social`: Trade и Leadership.

Для интерфейса используется отдельный `ui_group`, чтобы не терять дизайнерскую структуру:

- `weapon_mastery`, `tactical`, `armor`, `combat_support`
- `gathering`, `survival`
- `crafting`
- `trade`, `leadership`

Контракт поверхностей в коде хранится в `src/backend/features/game_catalog/skills/resources/contracts.py`:

- `actor_snapshot`: боевые навыки, влияющие на combat projection, плюс `skill_adaptation`.
- `encounter`: `skill_scouting`, `skill_pathfinder`, `skill_hunting`, `skill_taming`.
- `crafting`: `skill_first_aid`, `skill_weapon_craft`, `skill_armor_craft`, `skill_jewelry_craft`, `skill_alchemy`, `skill_engineering`, `skill_artifact_craft`.
- `inventory`: навыки экипировки и предметного производства, которые влияют на loadout, equip rules и качество предметов.

# 💾 Skills Data Schema

[⬅️ Назад: Skills Index](./README.md)

## 1. Структура DTO
Все навыки описываются единой моделью `SkillDTO`:

```python
class SkillDTO(BaseModel):
    skill_key: str              # "skill_swords"
    category: SkillCategory     # COMBAT / NON_COMBAT
    group: SkillGroup           # WEAPON_MASTERY, ARMOR...
    
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
from typing import TypeAlias

# --- ID TYPES ---

# Идентификатор персонажа (в БД это int, в Redis иногда str, но канонично int)
CharID: TypeAlias = int

# Идентификатор пользователя (Telegram ID)
UserID: TypeAlias = int

# Идентификатор сессии (UUID string)
SessionID: TypeAlias = str

# --- GAME DATA KEYS ---

# Ключ способности (например, "fireball_lvl1")
AbilityID: TypeAlias = str

# Ключ эффекта (например, "bleeding")
EffectID: TypeAlias = str

# Ключ предмета (например, "sword_iron")
ItemID: TypeAlias = str

# Ключ финта (например, "feint_sand")
FeintID: TypeAlias = str

# Ключ навыка (например, "swordsmanship")
SkillKey: TypeAlias = str

# --- MISC ---

# JSON-совместимый словарь (для payload)
JsonDict: TypeAlias = dict[str, str | int | float | bool | None | list | dict]

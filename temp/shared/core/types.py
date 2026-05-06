
# --- ID TYPES ---

# Идентификатор персонажа (в БД это int, в Redis иногда str, но канонично int)
type CharID = int

# Идентификатор пользователя (Telegram ID)
type UserID = int

# Идентификатор сессии (UUID string)
type SessionID = str

# --- GAME DATA KEYS ---

# Ключ способности (например, "fireball_lvl1")
type AbilityID = str

# Ключ эффекта (например, "bleeding")
type EffectID = str

# Ключ предмета (например, "sword_iron")
type ItemID = str

# Ключ финта (например, "feint_sand")
type FeintID = str

# Ключ навыка (например, "swordsmanship")
type SkillKey = str

# --- MISC ---

# JSON-совместимый словарь (для payload)
type JsonDict = dict[str, str | int | float | bool | None | list | dict]

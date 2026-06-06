from pydantic import BaseModel

from src.frontend.integrations.backend_api.game_lobby import GameLobbyResponse, LobbySlotPayload

DEFAULT_CHARACTER_AVATAR_URL = "/static/images/avatars/silhouette_m.webp"

VITAL_LABELS = {
    "hp": ("Здоровье", "hp"),
    "health": ("Здоровье", "hp"),
    "energy": ("Энергия", "energy"),
    "en": ("Энергия", "energy"),
    "concentration": ("Концентрация", "concentration"),
    "stamina": ("Концентрация", "concentration"),
    "vitality": ("Живучесть", "vitality"),
    "vita": ("Живучесть", "vitality"),
}

SLOT_LABELS = {
    "main_hand": "Основная рука",
    "off_hand": "Вторая рука",
    "head": "Голова",
    "helmet": "Голова",
    "chest": "Корпус",
    "chest_armor": "Кираса",
    "body": "Корпус",
    "legs": "Ноги",
    "boots": "Ступни",
    "gloves": "Кисти",
    "amulet": "Амулет",
    "ring": "Кольцо",
    "belt": "Пояс",
    "cloak": "Плащ",
    "weapon": "Оружие",
    "armor": "Броня",
}

SKILL_LABELS = {
    "skill_anatomy": "Анатомия",
    "skill_archery": "Стрельба",
    "skill_dual_wield": "Две руки",
    "skill_fencing": "Клинки",
    "skill_heavy_armor": "Тяжелая броня",
    "skill_light_armor": "Легкая броня",
    "skill_macing": "Ударное оружие",
    "skill_medium_armor": "Средняя броня",
    "skill_parrying": "Парирование",
    "skill_polearms": "Древковое оружие",
    "skill_ranged_combat": "Дальний бой",
    "skill_shield_mastery": "Щиты",
    "skill_swords": "Мечи",
    "skill_tactics": "Тактика",
    "skill_two_handed": "Двуручное оружие",
}


class CharacterVitalVM(BaseModel):
    key: str
    label: str
    value: str
    percent: int
    tone: str
    is_missing: bool = False


class CharacterAttributeVM(BaseModel):
    key: str
    label: str
    value: int


class CharacterItemVM(BaseModel):
    name: str
    meta: str
    rarity: str
    quantity: int


class CharacterSkillVM(BaseModel):
    label: str
    xp_label: str
    state: str
    is_unlocked: bool


class CharacterResourceVM(BaseModel):
    label: str
    value: int


class CharacterInventoryVM(BaseModel):
    equipped_count: int = 0
    backpack_count: int = 0
    resource_count: int = 0
    resources: list[CharacterResourceVM]


class LobbySlotVM(BaseModel):
    index: int
    is_empty: bool
    character_id: str | None = None
    name: str
    status: str
    presence_status: str
    presence_label: str
    presence_class: str
    avatar_url: str | None = None
    location_label: str
    updated_label: str
    vitals: list[CharacterVitalVM]
    attributes: list[CharacterAttributeVM]
    equipped_items: list[CharacterItemVM]
    inventory: CharacterInventoryVM
    skills: list[CharacterSkillVM]


class GameLobbyPageVM(BaseModel):
    title: str
    description: str
    primary_action_label: str
    message: str | None = None
    slots: list[LobbySlotVM]
    has_characters: bool
    can_start: bool
    max_slots: int
    can_create: bool


def build_lobby_page_vm(response: GameLobbyResponse) -> GameLobbyPageVM:
    payload = response.payload
    if payload is None:
        return GameLobbyPageVM(
            title="Порог",
            description="Лобби временно недоступно.",
            primary_action_label="Начать приключение",
            message=response.header.error,
            slots=[],
            has_characters=False,
            can_start=False,
            max_slots=4,
            can_create=False,
        )

    slots = [_build_slot_vm(slot) for slot in payload.slots]
    has_empty_slot = any(slot.is_empty for slot in slots)
    return GameLobbyPageVM(
        title=payload.title,
        description=payload.description,
        primary_action_label=payload.primary_action_label,
        message=payload.message,
        slots=slots,
        has_characters=any(not slot.is_empty for slot in slots),
        can_start=payload.can_start,
        max_slots=payload.max_slots,
        can_create=payload.can_start or has_empty_slot or not slots,
    )


def _build_slot_vm(slot: LobbySlotPayload) -> LobbySlotVM:
    is_empty = slot.is_empty or slot.character_id is None or slot.status.upper() == "VACANT"
    avatar_url = None if is_empty else slot.avatar_url or DEFAULT_CHARACTER_AVATAR_URL
    return LobbySlotVM(
        index=slot.index,
        is_empty=is_empty,
        character_id=slot.character_id,
        name=slot.name or "Пустой слот",
        status="Свободен" if is_empty else _status_label(slot.status),
        presence_status="offline" if is_empty else _presence_status(slot.presence_status),
        presence_label="Свободен" if is_empty else _presence_label(slot.presence_status),
        presence_class="free" if is_empty else _presence_status(slot.presence_status),
        avatar_url=avatar_url,
        location_label="-" if is_empty else _location_label(slot.location_id),
        updated_label="-" if is_empty else "Сводка обновлена",
        vitals=[] if is_empty else _character_vitals(slot.vitals),
        attributes=[] if is_empty else _character_attributes(slot.attributes),
        equipped_items=[] if is_empty else _character_items(slot.equipped_items),
        inventory=CharacterInventoryVM(resources=[]) if is_empty else _character_inventory(slot.inventory_summary),
        skills=[] if is_empty else _character_skills(slot.skills),
    )


def _status_label(status: str) -> str:
    normalized = status.strip().lower()
    labels = {
        "session_pending": "Синхронизация",
        "scenario": "Сценарий",
        "exploration": "Путешествие",
        "combat": "Бой",
        "arena": "Арена",
        "lobby": "Лобби",
    }
    return labels.get(normalized, status)


def _presence_status(status: str) -> str:
    normalized = status.strip().lower()
    return "online" if normalized == "online" else "offline"


def _presence_label(status: str) -> str:
    return "В сети" if _presence_status(status) == "online" else "Оффлайн"


def _location_label(location_id: str | None) -> str:
    return f"Локация {location_id}" if location_id else "Локация неизвестна"


def _character_vitals(vitals: dict) -> list[CharacterVitalVM]:
    result: list[CharacterVitalVM] = []
    for keys in (("hp", "health"), ("energy", "en"), ("concentration", "stamina"), ("vitality", "vita")):
        key = next((candidate for candidate in keys if candidate in vitals), None)
        if key is None:
            continue
        label, tone = VITAL_LABELS.get(key, (key.replace("_", " ").title(), key))
        result.append(_vital_vm(vitals, keys, label, tone))
    if not result:
        result.append(_vital_vm(vitals, ("hp", "health"), "Здоровье", "hp"))
    return result


def _vital_vm(vitals: dict, keys: tuple[str, ...], label: str, tone: str) -> CharacterVitalVM:
    raw = next((vitals.get(key) for key in keys if key in vitals), None)
    current, maximum = _read_vital_value(raw)
    if current is None:
        return CharacterVitalVM(key=keys[0], label=label, value="NO_DATA", percent=0, tone=tone, is_missing=True)
    if maximum and maximum > 0:
        percent = max(0, min(100, round((current / maximum) * 100)))
        value = f"{_clean_number(current)} / {_clean_number(maximum)}"
    else:
        percent = 100
        value = _clean_number(current)
    return CharacterVitalVM(key=keys[0], label=label, value=value, percent=percent, tone=tone)


def _read_vital_value(raw) -> tuple[float | None, float | None]:
    if isinstance(raw, dict):
        current = raw.get("current", raw.get("cur", raw.get("value", raw.get("amount"))))
        maximum = raw.get("max", raw.get("maximum", raw.get("limit")))
        return _float_or_none(current), _float_or_none(maximum)
    return _float_or_none(raw), None


def _float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def _character_attributes(attributes: dict[str, int]) -> list[CharacterAttributeVM]:
    labels = {
        "strength": "Сила",
        "agility": "Ловкость",
        "endurance": "Выносливость",
        "intellect": "Интеллект",
        "memory": "Память",
        "mental": "Ментальность",
        "perception": "Восприятие",
        "projection": "Проекция",
        "prediction": "Предвидение",
    }
    return [
        CharacterAttributeVM(key=key, label=label, value=int(attributes.get(key, 0) or 0))
        for key, label in labels.items()
        if key in attributes
    ]


def _character_items(items: list[dict]) -> list[CharacterItemVM]:
    result = []
    for item in items:
        slot = str(item.get("slot") or item.get("item_type") or "предмет")
        quantity = int(item.get("quantity") or 1)
        result.append(
            CharacterItemVM(
                name=str(item.get("name") or "Безымянный предмет"),
                meta=_slot_label(slot),
                rarity=str(item.get("rarity") or "shared"),
                quantity=quantity,
            )
        )
    return result


def _character_inventory(summary: dict) -> CharacterInventoryVM:
    resources: list[CharacterResourceVM] = []
    for bucket in ("currency", "resources", "components"):
        values = summary.get(bucket)
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            try:
                amount = int(value)
            except (TypeError, ValueError):
                continue
            if amount > 0:
                resources.append(CharacterResourceVM(label=_resource_label(str(key)), value=amount))
    return CharacterInventoryVM(
        equipped_count=int(summary.get("equipped_count") or 0),
        backpack_count=int(summary.get("backpack_count") or 0),
        resource_count=int(summary.get("resource_count") or 0),
        resources=resources[:6],
    )


def _character_skills(skills: list[dict]) -> list[CharacterSkillVM]:
    result = []
    for skill in skills[:6]:
        progress = (_float_or_none(skill.get("total_xp")) or 0) * 100
        result.append(
            CharacterSkillVM(
                label=_skill_label(str(skill.get("skill_key") or "Навык")),
                xp_label=f"{_clean_number(progress)}%",
                state=str(skill.get("progress_state") or ""),
                is_unlocked=bool(skill.get("is_unlocked")),
            )
        )
    return result


def _slot_label(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return SLOT_LABELS.get(normalized, normalized.replace("_", " ").title())


def _skill_label(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in SKILL_LABELS:
        return SKILL_LABELS[normalized]
    if normalized.startswith("skill_"):
        normalized = normalized.removeprefix("skill_")
    return normalized.replace("_", " ").title()


def _resource_label(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    labels = {
        "coin_copper": "Медные монеты",
        "currency_dust": "Пыль",
        "cloth_scrap": "Лоскуты ткани",
        "iron_scrap": "Железный лом",
        "mana_crystal_shard": "Осколки мана-кристалла",
        "core_fragment": "Фрагменты ядра",
    }
    return labels.get(normalized, normalized.replace("_", " ").title())

from pydantic import BaseModel

from src.frontend.integrations.backend_api.game_lobby import GameLobbyResponse, LobbySlotPayload

DEFAULT_CHARACTER_AVATAR_URL = "/static/images/avatars/silhouette_m.png"


class LobbySlotVM(BaseModel):
    index: int
    is_empty: bool
    character_id: str | None = None
    name: str
    status: str
    avatar_url: str | None = None


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
        title="Порог",
        description="Нейронные врата молчат. Задай имя и выбери облик, чтобы начать первое приключение.",
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
        avatar_url=avatar_url,
    )


def _status_label(status: str) -> str:
    labels = {
        "session_pending": "Синхронизация",
        "scenario": "Сценарий",
        "exploration": "Путешествие",
        "LOBBY": "Лобби",
    }
    return labels.get(status, status)

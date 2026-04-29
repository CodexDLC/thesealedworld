from pydantic import BaseModel

from src.frontend.integrations.backend_api.game_lobby import GameLobbyResponse, LobbySlotPayload


class LobbySlotVM(BaseModel):
    index: int
    is_empty: bool
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


def build_lobby_page_vm(response: GameLobbyResponse) -> GameLobbyPageVM:
    payload = response.payload
    if payload is None:
        return GameLobbyPageVM(
            title="The Threshold",
            description="The lobby is unavailable.",
            primary_action_label="Начать приключение",
            message=response.header.error,
            slots=[],
            has_characters=False,
        )

    slots = [_build_slot_vm(slot) for slot in payload.slots]
    return GameLobbyPageVM(
        title=payload.title,
        description=payload.description,
        primary_action_label=payload.primary_action_label,
        message=payload.message,
        slots=slots,
        has_characters=any(not slot.is_empty for slot in slots),
    )


def _build_slot_vm(slot: LobbySlotPayload) -> LobbySlotVM:
    return LobbySlotVM(
        index=slot.index,
        is_empty=slot.is_empty,
        name=slot.name or "VACANT_SLOT",
        status=slot.status,
        avatar_url=slot.avatar_url,
    )

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.backend.features.admin_players.api import (
    generate_admin_user_character,
    get_admin_character_detail,
    list_admin_user_characters,
)
from src.backend.features.admin_players.dto import (
    AdminPlayerCharacterListResponseDTO,
    AdminPlayerGenerateCharacterRequestDTO,
)


class FakeService:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.calls = []

    async def list_characters_for_user(self, user_id, *, limit: int, offset: int):
        self.calls.append((user_id, limit, offset))
        return AdminPlayerCharacterListResponseDTO(user_id=user_id, total=0, limit=limit, offset=offset)

    async def get_character_detail(self, character_id: int, *, inventory_limit: int, inventory_offset: int):
        self.calls.append((character_id, inventory_limit, inventory_offset))
        return None

    async def generate_for_user(self, user_id, payload):
        self.calls.append((user_id, payload.slot_index, payload.source_clan_id))
        return {"ok": True}


@pytest.mark.unit
async def test_list_admin_user_characters_delegates_to_service() -> None:
    service = FakeService()

    result = await list_admin_user_characters(service.user_id, object(), service, limit=10, offset=5)

    assert result.user_id == service.user_id
    assert result.limit == 10
    assert result.offset == 5
    assert service.calls == [(service.user_id, 10, 5)]


@pytest.mark.unit
async def test_get_admin_character_detail_returns_404_when_missing() -> None:
    service = FakeService()

    with pytest.raises(HTTPException) as exc_info:
        await get_admin_character_detail(404, object(), service, inventory_limit=20, inventory_offset=10)

    assert exc_info.value.status_code == 404
    assert service.calls == [(404, 20, 10)]


@pytest.mark.unit
async def test_generate_admin_user_character_delegates_to_service() -> None:
    service = FakeService()
    payload = AdminPlayerGenerateCharacterRequestDTO(slot_index=2, name="Hero", source_clan_id="clan-1")

    result = await generate_admin_user_character(service.user_id, payload, object(), service)

    assert result == {"ok": True}
    assert service.calls == [(service.user_id, 2, "clan-1")]

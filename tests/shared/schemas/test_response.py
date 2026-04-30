import pytest
from src.shared.schemas.response import GameStateHeader, CoreResponseDTO, CoreCompositeResponseDTO
from src.shared.enums.domain import CoreDomain

@pytest.mark.unit
class TestResponseSchemas:
    def test_game_state_header_initialization(self):
        header = GameStateHeader(
            current_state=CoreDomain.LOBBY,
            previous_state=CoreDomain.ARENA,
            error="Something went wrong"
        )
        assert header.current_state == CoreDomain.LOBBY
        assert header.previous_state == CoreDomain.ARENA
        assert header.error == "Something went wrong"
        assert len(header.transaction_id) == 32

    def test_core_response_dto_generic(self):
        header = GameStateHeader(current_state=CoreDomain.LOBBY)
        payload = {"user_id": 123}
        dto = CoreResponseDTO[dict](header=header, payload=payload, payload_type="User")

        assert dto.header == header
        assert dto.payload == payload
        assert dto.payload_type == "User"

    def test_core_composite_response_dto(self):
        header = GameStateHeader(current_state=CoreDomain.EXPLORATION)
        payload = "World data"
        menu = {"options": ["back"]}
        dto = CoreCompositeResponseDTO[str, dict](
            header=header,
            payload=payload,
            menu_payload=menu,
            payload_type="World"
        )

        assert dto.payload == payload
        assert dto.menu_payload == menu

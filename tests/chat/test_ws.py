from src.backend.chat.api.ws import _with_session_scope
from src.backend.chat.dto.message import IncomingMessageDTO


def test_zone_message_without_scope_uses_session_location() -> None:
    msg = IncomingMessageDTO(channel="zone", content="hello")

    scoped = _with_session_scope(msg, {"location_id": "52_52"})

    assert scoped is not None
    assert scoped.scope_id == "52_52"


def test_zone_message_without_location_is_rejected() -> None:
    msg = IncomingMessageDTO(channel="zone", content="hello")

    assert _with_session_scope(msg, {}) is None


def test_global_message_does_not_get_location_scope() -> None:
    msg = IncomingMessageDTO(channel="global", content="hello")

    scoped = _with_session_scope(msg, {"location_id": "52_52"})

    assert scoped is msg
    assert scoped.scope_id is None

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.backend.realtime.dto.envelope import ChatSendPayload, IncomingEnvelopeDTO, OutgoingEnvelopeDTO


@pytest.mark.unit
def test_chat_send_payload_validates_channel_and_content() -> None:
    payload = ChatSendPayload.model_validate({"channel": "global", "content": "hi"})
    assert payload.channel == "global"
    assert payload.scope_id is None


@pytest.mark.unit
def test_incoming_envelope_accepts_chat_send() -> None:
    envelope = IncomingEnvelopeDTO.model_validate(
        {"type": "chat.send", "payload": {"channel": "zone", "content": "hi"}}
    )
    assert envelope.type == "chat.send"


@pytest.mark.unit
def test_incoming_envelope_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        IncomingEnvelopeDTO.model_validate({"type": "system.shutdown", "payload": {}})


@pytest.mark.unit
def test_incoming_envelope_rejects_missing_type() -> None:
    with pytest.raises(ValidationError):
        IncomingEnvelopeDTO.model_validate({"payload": {"channel": "global", "content": "x"}})


@pytest.mark.unit
def test_chat_send_payload_rejects_empty_content() -> None:
    with pytest.raises(ValidationError):
        ChatSendPayload.model_validate({"channel": "global", "content": ""})


@pytest.mark.unit
def test_outgoing_envelope_carries_presentation() -> None:
    envelope = OutgoingEnvelopeDTO.model_validate(
        {"type": "chat.message", "presentation": "chat", "payload": {"id": "1"}}
    )
    assert envelope.presentation == "chat"

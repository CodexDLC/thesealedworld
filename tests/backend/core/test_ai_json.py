from pydantic import BaseModel

from src.backend.core.ai_json import parse_ai_json_mapping, parse_ai_json_model


class ExamplePayload(BaseModel):
    name: str


def test_parse_ai_json_mapping_strips_markdown_fence() -> None:
    assert parse_ai_json_mapping('```json\n{"name": "ok"}\n```', context="test") == {"name": "ok"}


def test_parse_ai_json_model_validates_payload() -> None:
    parsed = parse_ai_json_model('```\n{"name": "ok"}\n```', ExamplePayload, context="test")

    assert parsed == ExamplePayload(name="ok")

from __future__ import annotations

import json
from typing import Any

from loguru import logger as log
from pydantic import BaseModel, ValidationError


def parse_ai_json_mapping(raw_response: Any, *, context: str = "ai") -> dict[str, Any] | None:
    payload = parse_ai_json(raw_response, context=context)
    if isinstance(payload, dict):
        return payload
    log.bind(context=context).warning("AiJsonResponseNotObject")
    return None


def parse_ai_json_model[TModel: BaseModel](
    raw_response: Any, model_type: type[TModel], *, context: str = "ai"
) -> TModel | None:
    payload = parse_ai_json(raw_response, context=context)
    if payload is None:
        return None
    try:
        return model_type.model_validate(payload)
    except ValidationError:
        log.bind(context=context, payload=payload).warning("AiJsonResponseSchemaValidationFailed")
        return None


def parse_ai_json(raw_response: Any, *, context: str = "ai") -> Any | None:
    if raw_response is None:
        return None
    if not isinstance(raw_response, str):
        return raw_response

    text = _strip_markdown_json_fence(raw_response)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.bind(context=context, raw_response=raw_response).warning("AiJsonResponseInvalid")
        return None


def _strip_markdown_json_fence(raw_text: str) -> str:
    text = raw_text.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()

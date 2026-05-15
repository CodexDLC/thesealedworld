from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.generation_ai.dto import AIGenerationTaskSpecDTO


def build_generation_task_identity_key(spec: AIGenerationTaskSpecDTO) -> str:
    payload: dict[str, Any] = {
        "task_type": spec.task_type,
        "entity_type": spec.entity_type,
        "entity_id": spec.entity_id,
        "season_id": spec.season_id or "",
        "asset_hash": spec.asset_hash or "",
        "input_payload": spec.input_payload,
        "prompt_payload": spec.prompt_payload,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"ai:{digest}"

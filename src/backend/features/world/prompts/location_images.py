from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.backend.features.world.prompts.location_profiles.d4_capital_hub import build_d4_capital_hub_prompt

LocationImagePromptBuilder = Callable[[dict[str, Any]], str]

LOCATION_IMAGE_PROMPT_BUILDERS: dict[str, LocationImagePromptBuilder] = {
    "d4_capital_hub": build_d4_capital_hub_prompt,
}


def build_location_image_prompt(payload: dict[str, Any]) -> str:
    """Build a plain image prompt for a generated world location background."""
    visual_overrides = _safe_dict(payload.get("visual_overrides"))
    image_profile = str(visual_overrides.get("image_profile") or payload.get("image_profile") or "d4_capital_hub")
    builder = LOCATION_IMAGE_PROMPT_BUILDERS.get(image_profile)
    if builder is None:
        raise ValueError(f"Unsupported location image profile: {image_profile}")
    return builder(payload)


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}

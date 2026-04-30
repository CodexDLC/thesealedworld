from typing import Any

from pydantic import BaseModel, Field

from src.shared.schemas import ScenarioPayloadDTO


class ScenarioExtraDataVM(BaseModel):
    """Validated metadata for the scenario UI."""

    char_id: int | None = None
    quest_key: str | None = None
    background_url: str | None = None
    show_left_sidebar: bool = False
    show_right_sidebar: bool = False
    quest_title: str | None = None
    rewards: list[dict[str, Any]] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class ScenarioPageVM(BaseModel):
    """The root object passed to the scenario templates."""

    scenario: ScenarioPayloadDTO
    extra_data: ScenarioExtraDataVM
    transaction_id: str
    domain: str
    user: Any | None = None


def build_scenario_page_vm(response: Any, user: Any = None) -> ScenarioPageVM:
    """Assembles and validates the ScenarioPageVM from raw API response."""
    payload = response.payload

    # Extract extra data with defaults
    raw_extra = getattr(payload, "extra_data", {}) or {}

    extra_vm = ScenarioExtraDataVM(
        char_id=raw_extra.get("char_id"),
        quest_key=raw_extra.get("quest_key"),
        background_url=raw_extra.get("background_url"),
        show_left_sidebar=bool(raw_extra.get("show_left_sidebar", False)),
        show_right_sidebar=bool(raw_extra.get("show_right_sidebar", False)),
        quest_title=raw_extra.get("quest_title"),
        rewards=raw_extra.get("rewards", []),
        flags=raw_extra.get("flags", []),
    )

    return ScenarioPageVM(
        scenario=payload,
        extra_data=extra_vm,
        transaction_id=response.header.transaction_id,
        domain=response.header.current_state,
        user=user,
    )

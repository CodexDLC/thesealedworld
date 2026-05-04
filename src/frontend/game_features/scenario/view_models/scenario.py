from typing import Any

from pydantic import BaseModel, Field

from src.frontend.game_features.session.view_models.nav import build_game_nav
from src.shared.schemas import ScenarioPayloadDTO
from src.shared.schemas.character_status import CharacterActorCoreDTO


class ScenarioExtraDataVM(BaseModel):
    """Validated metadata for the scenario UI."""

    char_id: int | None = None
    quest_key: str | None = None
    node_type: str = "event"
    phase: str | None = None
    speaker: str | None = None
    background_url: str | None = None
    show_left_sidebar: bool = False
    show_right_sidebar: bool = False
    quest_title: str | None = None
    rewards: list[dict[str, Any]] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    left_panel: dict[str, Any] = Field(default_factory=dict)
    right_panel: dict[str, Any] = Field(default_factory=dict)


class ScenarioPageVM(BaseModel):
    """The root object passed to the scenario templates."""

    scenario: ScenarioPayloadDTO
    extra_data: ScenarioExtraDataVM
    transaction_id: str
    domain: str
    char_id: int | None = None
    character_status: CharacterActorCoreDTO | None = None
    nav: dict[str, dict[str, Any]] = Field(default_factory=dict)
    user: Any | None = None


def build_scenario_page_vm(
    response: Any,
    user: Any = None,
    *,
    character_status: CharacterActorCoreDTO | None = None,
) -> ScenarioPageVM:
    """Assembles and validates the ScenarioPageVM from raw API response."""
    payload = response.payload

    # Extract extra data with defaults
    raw_extra = getattr(payload, "extra_data", {}) or {}

    extra_vm = ScenarioExtraDataVM(
        char_id=raw_extra.get("char_id"),
        quest_key=raw_extra.get("quest_key"),
        node_type=getattr(payload, "node_type", raw_extra.get("node_type", "event")),
        phase=getattr(payload, "phase", raw_extra.get("phase")),
        speaker=getattr(payload, "speaker", raw_extra.get("speaker")),
        background_url=raw_extra.get("background_url"),
        show_left_sidebar=bool(raw_extra.get("show_left_sidebar", False)),
        show_right_sidebar=bool(raw_extra.get("show_right_sidebar", False)),
        quest_title=raw_extra.get("quest_title"),
        rewards=raw_extra.get("rewards", []),
        flags=raw_extra.get("flags", []),
        left_panel=raw_extra.get("left_panel", {}),
        right_panel=raw_extra.get("right_panel", {}),
    )
    char_id = extra_vm.char_id or getattr(character_status, "char_id", None)

    return ScenarioPageVM(
        scenario=payload,
        extra_data=extra_vm,
        transaction_id=response.header.transaction_id,
        domain=response.header.current_state,
        char_id=char_id,
        character_status=character_status,
        nav=build_game_nav(state=response.header.current_state, char_id=char_id or 0),
        user=user,
    )

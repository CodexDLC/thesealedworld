from __future__ import annotations

import uuid

from src.shared.schemas.exploration import EncounterDTO, EncounterOptionDTO, EncounterType

CONTINUE_LABEL = "тяжело вздохнуть с пониманием и пойти дальше ))"


def build_placeholder_discovery(
    *,
    discovery_type: str,
    title: str,
    description: str,
    loc_id: str,
) -> EncounterDTO:
    return EncounterDTO(
        id=f"{discovery_type}-{uuid.uuid4().hex[:12]}",
        type=EncounterType.NARRATIVE,
        title=title,
        description=description,
        options=[EncounterOptionDTO(id="continue", label=CONTINUE_LABEL, style="secondary")],
        metadata={
            "kind": "discovery_placeholder",
            "discovery_type": discovery_type,
            "loc_id": loc_id,
            "implemented": False,
        },
    )

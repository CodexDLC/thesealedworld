import pytest
from pydantic import ValidationError

from src.backend.features.actor_state.dto import ActorContextDTO


@pytest.mark.unit
def test_actor_context_contract_allows_unrequested_sections_as_null() -> None:
    context = ActorContextDTO.model_validate(
        {
            "meta": {
                "actor_type": "player",
                "actor_id": 1,
                "name": "CodexDLC",
                "role": "player",
                "tags": ["player"],
            },
            "source": {"character_id": 1, "db_refs": {"characters": 1}},
            "combat": {"math_model": {"attributes": {}}, "loadout": {}, "skills": {}},
        }
    )

    dumped = context.model_dump(mode="json")
    assert dumped["schema_version"] == 1
    assert dumped["combat"] == {"math_model": {"attributes": {}}, "loadout": {}, "skills": {}}
    assert dumped["inventory"] is None
    assert dumped["runtime"] is None
    assert dumped["status"] is None


@pytest.mark.unit
def test_actor_context_requires_meta_and_source() -> None:
    with pytest.raises(ValidationError):
        ActorContextDTO.model_validate({"meta": {"actor_type": "player", "actor_id": 1, "name": "Hero"}})


@pytest.mark.unit
def test_actor_context_rejects_unknown_top_level_sections() -> None:
    with pytest.raises(ValidationError):
        ActorContextDTO.model_validate(
            {
                "meta": {"actor_type": "player", "actor_id": 1, "name": "Hero"},
                "source": {},
                "unknown": {},
            }
        )

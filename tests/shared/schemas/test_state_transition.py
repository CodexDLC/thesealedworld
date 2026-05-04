from src.shared.enums import CoreDomain
from src.shared.schemas import StateTransitionDTO


def test_state_transition_dto_is_launch_context():
    dto = StateTransitionDTO(
        char_id=7,
        target_state=CoreDomain.SCENARIO,
        reason="quest_started",
        quest_key="awakening_rift",
    )

    assert dto.char_id == 7
    assert dto.target_state == CoreDomain.SCENARIO
    assert dto.quest_key == "awakening_rift"

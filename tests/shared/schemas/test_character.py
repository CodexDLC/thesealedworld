import uuid
from datetime import UTC, datetime

import pytest

from src.shared.schemas.character import CharacterAttributesReadDTO, CharacterReadDTO


@pytest.mark.unit
def test_character_read_dto_accepts_web_user_uuid_and_avatar() -> None:
    user_id = uuid.uuid4()

    dto = CharacterReadDTO.model_validate(
        {
            "character_id": 1,
            "user_id": user_id,
            "name": "Hero",
            "gender": "male",
            "avatar_url": "/static/images/avatars/hero.png",
            "game_stage": "in_game",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )

    assert dto.user_id == user_id
    assert dto.avatar_url == "/static/images/avatars/hero.png"


@pytest.mark.unit
def test_character_read_dto_keeps_legacy_integer_user_id() -> None:
    dto = CharacterReadDTO.model_validate(
        {
            "character_id": 1,
            "user_id": 42,
            "name": "Hero",
            "gender": "male",
            "game_stage": "in_game",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )

    assert dto.user_id == 42
    assert dto.avatar_url is None


@pytest.mark.unit
def test_character_attributes_read_dto_accepts_current_attribute_names() -> None:
    dto = CharacterAttributesReadDTO.model_validate(
        {
            "character_id": 1,
            "strength": 10,
            "agility": 11,
            "endurance": 12,
            "intellect": 13,
            "memory": 14,
            "mental": 15,
            "perception": 16,
            "projection": 17,
            "prediction": 18,
        }
    )

    assert dto.intellect == 13
    assert dto.memory == 14
    assert dto.mental == 15
    assert dto.projection == 17
    assert dto.prediction == 18
    assert dto.intelligence == 13
    assert dto.wisdom == 14
    assert dto.men == 15
    assert dto.charisma == 17
    assert dto.luck == 18


@pytest.mark.unit
def test_character_attributes_read_dto_keeps_legacy_attribute_names() -> None:
    dto = CharacterAttributesReadDTO.model_validate(
        {
            "character_id": 1,
            "strength": 10,
            "agility": 11,
            "endurance": 12,
            "intelligence": 13,
            "wisdom": 14,
            "men": 15,
            "perception": 16,
            "charisma": 17,
            "luck": 18,
        }
    )

    assert dto.intellect == 13
    assert dto.memory == 14
    assert dto.mental == 15
    assert dto.projection == 17
    assert dto.prediction == 18

import pytest
from pydantic import ValidationError

from src.shared.schemas import CreateCharacterRequestDTO


@pytest.mark.parametrize(
    ("raw_name", "normalized"),
    [
        ("Ada", "Ada"),
        ("Ворон_7", "Ворон_7"),
        ("DarkLord_9", "DarkLord_9"),
        ("  Ada  ", "Ada"),
    ],
)
def test_character_name_accepts_mvp_contract(raw_name: str, normalized: str) -> None:
    dto = CreateCharacterRequestDTO(name=raw_name, gender="female")

    assert dto.name == normalized


@pytest.mark.parametrize(
    "raw_name",
    [
        "Ad",
        "A" * 17,
        "_Ada",
        "Ada_",
        "Ada__Prime",
        "123",
        "Аda",
        "Ada-Prime",
        "Ada Prime",
    ],
)
def test_character_name_rejects_invalid_mvp_names(raw_name: str) -> None:
    with pytest.raises(ValidationError):
        CreateCharacterRequestDTO(name=raw_name, gender="female")

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

CHARACTER_NAME_MIN_LENGTH = 3
CHARACTER_NAME_MAX_LENGTH = 16

_MULTIPLE_UNDERSCORES = "__"


@dataclass(frozen=True, slots=True)
class CharacterName:
    display: str
    key: str


class CharacterNameError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_character_name(value: str) -> CharacterName:
    display = unicodedata.normalize("NFKC", str(value)).strip()
    _validate_display_name(display)
    return CharacterName(display=display, key=character_name_key(display))


def character_name_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).strip()
    return normalized.casefold().replace("ё", "е")


def _validate_display_name(name: str) -> None:
    if len(name) < CHARACTER_NAME_MIN_LENGTH or len(name) > CHARACTER_NAME_MAX_LENGTH:
        raise CharacterNameError(
            "invalid_length",
            f"Имя должно быть от {CHARACTER_NAME_MIN_LENGTH} до {CHARACTER_NAME_MAX_LENGTH} символов",
        )
    if name.startswith("_") or name.endswith("_"):
        raise CharacterNameError("edge_underscore", "Имя не может начинаться или заканчиваться подчеркиванием")
    if _MULTIPLE_UNDERSCORES in name:
        raise CharacterNameError("double_underscore", "Имя не может содержать двойное подчеркивание")

    has_latin = False
    has_cyrillic = False
    has_letter = False

    for char in name:
        if char == "_":
            continue
        if char.isascii() and char.isdecimal():
            continue
        if _is_latin(char):
            has_latin = True
            has_letter = True
            continue
        if _is_cyrillic(char):
            has_cyrillic = True
            has_letter = True
            continue
        raise CharacterNameError(
            "invalid_characters",
            "Имя может содержать только кириллицу, латиницу, цифры и подчеркивание",
        )

    if not has_letter:
        raise CharacterNameError("letters_required", "Имя должно содержать хотя бы одну букву")
    if has_latin and has_cyrillic:
        raise CharacterNameError("mixed_scripts", "Имя не может смешивать кириллицу и латиницу")


def _is_latin(char: str) -> bool:
    return ("a" <= char <= "z") or ("A" <= char <= "Z")


def _is_cyrillic(char: str) -> bool:
    return "\u0400" <= char <= "\u04ff"

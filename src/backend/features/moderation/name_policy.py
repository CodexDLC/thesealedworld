from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from src.shared.utils.character_name import (
    CharacterName,
    CharacterNameError,
    character_name_key,
    normalize_character_name,
)

_RESOURCES_DIR = Path(__file__).parent / "resources"


@dataclass(frozen=True, slots=True)
class CharacterNamePolicyResult:
    display: str
    key: str


class CharacterNamePolicy:
    def validate(self, value: str) -> CharacterNamePolicyResult:
        name = normalize_character_name(value)
        self._validate_reserved(name)
        self._validate_forbidden(name)
        return CharacterNamePolicyResult(display=name.display, key=name.key)

    def check(self, value: str) -> tuple[CharacterNamePolicyResult | None, str | None, str | None]:
        try:
            result = self.validate(value)
        except CharacterNameError as exc:
            return None, exc.code, exc.message
        return result, None, None

    @cached_property
    def reserved_name_keys(self) -> frozenset[str]:
        return frozenset(_load_resource_keys(_RESOURCES_DIR / "reserved_names.txt"))

    @cached_property
    def forbidden_name_keys(self) -> tuple[str, ...]:
        return tuple(sorted(_load_resource_keys(_RESOURCES_DIR / "forbidden_names.txt"), key=len, reverse=True))

    def _validate_reserved(self, name: CharacterName) -> None:
        if name.key in self.reserved_name_keys:
            raise CharacterNameError("reserved_name", "Это имя зарезервировано")

    def _validate_forbidden(self, name: CharacterName) -> None:
        for forbidden in self.forbidden_name_keys:
            if forbidden and forbidden in name.key:
                raise CharacterNameError("forbidden_name", "Это имя запрещено")


def _load_resource_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()

    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.split("#", 1)[0].strip()
        if not value:
            continue
        for item in re.split(r"[,;]", value):
            item = item.strip()
            if item:
                keys.add(character_name_key(item))
    return keys

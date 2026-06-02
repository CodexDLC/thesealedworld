"""Preview fixture registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any


@dataclass(frozen=True)
class PreviewFixture:
    context: dict[str, Any]
    template: str
    title: str
    description: str = ""
    body_class: str = ""
    viewport_presets: dict[str, tuple[int, int]] = field(
        default_factory=lambda: {
            "desktop": (1440, 900),
            "tablet": (768, 1024),
            "mobile": (390, 844),
        }
    )


def build_fixture(fixture_key: str, params: dict[str, str] | None = None) -> PreviewFixture:
    domain, _, name = fixture_key.partition("/")
    if not domain or not name:
        raise ValueError("Fixture must use '<domain>/<name>', for example 'combat/active_8_abilities'.")

    module = import_module(f"tools.game_preview.fixtures.{domain}")
    builder = getattr(module, "build_fixture", None)
    if builder is None:
        raise ValueError(f"Fixture domain {domain!r} does not expose build_fixture().")
    return builder(name, params or {})

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WorldThemeDTO(BaseModel):
    """Runtime glass/interface tint derived from world anchor pressure."""

    source: str = "anchor_field"
    loc_id: str | None = None
    mode: Literal["safe", "anchor", "hybrid"] = "safe"
    dominant_anchor: str | None = None
    intensity: float = 0.0
    weights: dict[str, float] = Field(default_factory=dict)
    accent: str = "#ffaa00"
    accent_dim: str = "rgba(255, 170, 0, 0.4)"
    accent_soft: str = "rgba(255, 170, 0, 0.08)"
    accent_border: str = "rgba(255, 170, 0, 0.22)"
    accent_glow: str = "rgba(255, 170, 0, 0.30)"
    glass: str = "rgba(12, 12, 16, 0.72)"
    css_vars: dict[str, str] = Field(default_factory=dict)

    def model_post_init(self, __context: object) -> None:
        if self.css_vars:
            return
        self.css_vars = {
            "--world-accent": self.accent,
            "--world-accent-dim": self.accent_dim,
            "--world-accent-soft": self.accent_soft,
            "--world-accent-border": self.accent_border,
            "--world-accent-glow": self.accent_glow,
            "--world-glass": self.glass,
            "--world-intensity": str(self.intensity),
        }

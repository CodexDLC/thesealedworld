"""Policy artifact contract: weights vector + metadata, JSON-serialisable."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Keys the trainer and default policy normalize against. Adding a new tag
# elsewhere (action_space or scorer) only needs a matching key here so
# trainers seed an explicit zero instead of an unknown column.
DEFAULT_WEIGHT_KEYS: tuple[str, ...] = (
    # Target-state features
    "target_low_hp",
    "target_high_hp",
    "finishable",
    # Universal action signals
    "expected_damage",
    "damage_tag",
    "multi_target",
    # Anti-defence axes (scaled by the target's defence value)
    "anti_block",
    "anti_parry",
    "anti_evasion",
    "armor_bypass",
    # Effects on target
    "control",
    "bleed",
    "debuff",
    # Self-care axes (scaled by the bot's own state)
    "heal",
    "self_buff",
    "defense",
    "preparation",
    "counter",
    # Purchase-group preferences (let policy learn to prefer one slot type)
    "group_basic",
    "group_tactical",
    "group_weapon",
    # Resource pressure (when the bot already carries these tokens)
    "blood_resource",
    "counter_resource",
    "gift_resource",
    # Cost penalties
    "token_cost",
    "stamina_cost",
    "self_low_hp_resource_save",
    "self_low_stamina_save",
    # Controlled exploration
    "randomness",
)


class Policy(BaseModel):
    """One trained or hand-tuned set of weights for the combat scorer."""

    policy_id: str = "default"
    version: int = 1
    weights: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get(self, key: str, default: float = 0.0) -> float:
        """Return a weight, falling back to ``default`` if absent."""
        value = self.weights.get(key)
        if value is None:
            return default
        return float(value)

    @classmethod
    def with_defaults(cls, weights: dict[str, float] | None = None, **kwargs: Any) -> Policy:
        """Build a policy filling missing default keys with zero weights."""
        merged = {key: 0.0 for key in DEFAULT_WEIGHT_KEYS}
        if weights:
            merged.update({k: float(v) for k, v in weights.items()})
        return cls(weights=merged, **kwargs)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True)

    @classmethod
    def from_json_text(cls, raw: str) -> Policy:
        return cls.model_validate(json.loads(raw))

    @classmethod
    def from_path(cls, path: Path) -> Policy:
        return cls.from_json_text(path.read_text(encoding="utf-8"))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

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
    "energy_cost",
    "self_low_hp_resource_save",
    "self_low_stamina_save",
    "finishable_resource_save",
    # Preparation awareness (PR2): magnitudes are stored positive, the scorer
    # applies the appropriate sign. ``prep_threat_penalty`` is *subtracted* when
    # attacking through a dangerous prep; ``dispel_prep`` is *added* when the
    # action dispels prep stacks; ``heal_dedup_penalty`` is *subtracted* when
    # the bot already has a heal-promising prep active.
    "prep_threat_penalty",
    "dispel_prep",
    "heal_dedup_penalty",
    # Team awareness (PR4): magnitudes stored positive, scorer applies sign.
    # ``team_focus`` is *added* per ally already aiming at the target;
    # ``team_focus_pile_on`` is *added* once when the target is already
    # controlled and an ally is already focusing it; ``team_dedup_control``
    # is *subtracted* when this action would queue a duplicate control on a
    # target an ally is already controlling.
    "team_focus",
    "team_focus_pile_on",
    "team_dedup_control",
    # Cross-turn memory (PR5): observed-behaviour bonuses for anti-X tags
    # and small biases for sticky focus and variety. All stored positive;
    # the scorer applies the appropriate sign per branch.
    "observed_parry_rate",
    "observed_evasion_rate",
    "observed_block_rate",
    "sticky_target_bonus",
    "repeat_feint_penalty",
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

    def with_overlay(self, overlay: dict[str, float]) -> Policy:
        """Return a derived policy with weights multiplied by ``overlay``.

        Pure: the source policy is not mutated. Unknown overlay keys are
        ignored (overlays are cross-cutting tactical multipliers, not a way
        to *introduce* weights — those belong in the underlying policy).
        """
        if not overlay:
            return self
        new_weights = dict(self.weights)
        for key, multiplier in overlay.items():
            if key in new_weights:
                new_weights[key] = float(new_weights[key]) * float(multiplier)
        return Policy(
            policy_id=self.policy_id,
            version=self.version,
            weights=new_weights,
            metadata=dict(self.metadata),
        )

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

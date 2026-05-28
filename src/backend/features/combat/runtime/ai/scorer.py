"""Pure scoring of a legal action under a policy."""

from __future__ import annotations

import random

from src.backend.features.combat.runtime.ai.action_space import LegalAction  # noqa: TC001
from src.backend.features.combat.runtime.ai.observation import (  # noqa: TC001
    SelfObservation,
    TargetObservation,
)
from src.backend.features.combat.runtime.ai.policy import Policy  # noqa: TC001


class PolicyScorer:
    """Compute a deterministic score for one ``LegalAction`` under one policy.

    The score is a dot product between a feature vector built from the
    observations and the action tags and a weight vector from the policy.
    Optional bounded Gaussian noise is gated by ``policy.weights["randomness"]``
    and a seeded :class:`random.Random` so unit tests stay reproducible.
    """

    @staticmethod
    def score(
        self_obs: SelfObservation,
        target_obs: TargetObservation,
        action: LegalAction,
        policy: Policy,
        rng: random.Random | None = None,
    ) -> float:
        score = 0.0

        # === Target-state features (apply to every action against this target) ===
        score += policy.get("target_low_hp") * (1.0 - target_obs.hp_pct)
        score += policy.get("target_high_hp") * target_obs.hp_pct
        if target_obs.finishable:
            score += policy.get("finishable")
        if target_obs.has_control:
            score += policy.get("control") * 0.4
        if target_obs.has_bleed:
            score += policy.get("bleed") * 0.4

        # === Action-tag features ===
        tags = action.tags

        # Baseline expected damage for any attack action.
        score += policy.get("expected_damage") * _baseline_damage_factor(target_obs)

        # Counter-defence bonuses: weight is multiplied by the defence value it
        # bypasses, so anti_block matters more against high-block targets.
        if "anti_block" in tags:
            score += policy.get("anti_block") * target_obs.block
        if "anti_parry" in tags:
            score += policy.get("anti_parry") * target_obs.parry
        if "anti_evasion" in tags:
            score += policy.get("anti_evasion") * target_obs.evasion
        if "armor_bypass" in tags:
            score += policy.get("armor_bypass") * _armor_density(target_obs)
        if "control" in tags:
            score += policy.get("control")
        if "bleed" in tags:
            score += policy.get("bleed")
        if "debuff" in tags:
            score += policy.get("debuff")
        if "multi_target" in tags:
            score += policy.get("multi_target") * max(0, self_obs.alive_enemy_count - 1)
        if "preparation" in tags:
            score += policy.get("preparation")
        if "counter" in tags:
            counter_weight = policy.get("counter")
            score += counter_weight * (0.5 + target_obs.counter_attack_chance)
        if "damage_tag" in tags:
            score += policy.get("damage_tag")

        # === Self-care axes: weight scaled by how badly the bot needs it ===
        if "heal" in tags:
            # Heal is worth more the lower we are; capped at 0.7 HP.
            score += policy.get("heal") * max(0.0, 0.7 - self_obs.hp_pct)
        if "self_buff" in tags:
            score += policy.get("self_buff")
        if "defense" in tags:
            # Defence becomes valuable as the bot loses HP.
            score += policy.get("defense") * (1.0 - self_obs.hp_pct)

        # === Purchase-group preferences ===
        if "group_basic" in tags:
            score += policy.get("group_basic")
        if "group_tactical" in tags:
            score += policy.get("group_tactical")
        if "group_weapon" in tags:
            score += policy.get("group_weapon")

        # === Resource-pool signals: bot already carries these tokens ===
        if self_obs.tokens.get("blood", 0) > 0:
            score += policy.get("blood_resource") * min(3, int(self_obs.tokens["blood"]))
        if self_obs.tokens.get("counter", 0) > 0 and "counter" in tags:
            score += policy.get("counter_resource")
        if self_obs.tokens.get("gift", 0) > 0:
            score += policy.get("gift_resource")

        # === Resource cost features ===
        token_total = sum(int(amount) for amount in action.cost.values())
        score += policy.get("token_cost") * token_total
        score += policy.get("stamina_cost") * action.stamina_cost

        if action.feint_id is not None:
            if self_obs.low_hp:
                score += policy.get("self_low_hp_resource_save")
            if self_obs.low_stamina:
                score += policy.get("self_low_stamina_save")

        # === Controlled exploration noise ===
        randomness = policy.get("randomness")
        if randomness > 0.0 and rng is not None:
            noise = rng.gauss(0.0, randomness)
            # Clamp to ±3 sigma so a single sample cannot flip strong signals.
            noise = max(-3.0 * randomness, min(3.0 * randomness, noise))
            score += noise

        return score


def _baseline_damage_factor(target_obs: TargetObservation) -> float:
    """Cheap proxy for "how much real damage is left in this target".

    Avoids touching the resolver: it scales linearly with remaining HP and
    is dampened by physical mitigation. Not a damage prediction — a
    relative ordering signal.
    """
    mitigation = max(0.0, 1.0 - target_obs.physical_resistance)
    return target_obs.hp_pct * mitigation


def _armor_density(target_obs: TargetObservation) -> float:
    """Normalised armor footprint, capped so a huge raw value cannot dominate."""
    return min(1.0, target_obs.armor / 50.0)

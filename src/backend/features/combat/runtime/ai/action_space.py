"""Legal action enumeration for the AI brain.

The action space is the cartesian product of *(target, attack option)* where an
attack option is either a plain ``attack`` or ``attack + feint`` for each
affordable feint sitting in ``bot.meta.feints.hand`` at decision time.

Tags drive the scorer. They are extracted from the feint catalog entry:

- ``applicability_tags`` are copied as-is (post-overhaul main pre-populates
  these with the right vocabulary: ``anti_parry``, ``heal``, ``preparation``,
  ``counter``, ``debuff``, ``shield_bash``, ``control``, etc.).
- ``cost.tactics`` keys add token-derived tags (e.g. paying a ``parry``
  token implies ``anti_parry``).
- ``modifier_applications`` / ``pipeline_mutations`` / ``effects`` /
  ``triggers`` are inspected as a fallback for entries that do not carry
  an explicit ``applicability_tag``.
- ``purchase_group`` adds ``group_basic`` / ``group_weapon`` /
  ``group_tactical`` so the scorer can learn cost-vs-school preferences.
- ``preparation_effects`` with a ``source`` actor add ``self_buff`` (and
  ``heal`` when ``params.heal_*`` is present).
- ``effects`` aimed at the target add ``debuff``.
- ``shield_guard_damage_ratio > 0`` adds ``shield_damage``.

The runtime stays in sync with content changes without code edits as long as
designers keep filling ``applicability_tags``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.backend.features.combat.dto.actor import ActorSnapshot  # noqa: TC001
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.engine.feint_service import FeintService

ATTACK_ACTION = "attack"
INSTANT_ACTION = "instant"

# Tactic-token name -> action tag. All 9 tokens from
# game_catalog/combat/resources/tokens.py are mapped.
_TACTIC_TOKEN_TAGS: dict[str, str] = {
    "hit": "damage_tag",
    "crit": "damage_tag",
    "tempo": "preparation",
    "block": "anti_block",
    "parry": "anti_parry",
    "dodge": "anti_evasion",
    "counter": "counter_resource",
    "blood": "blood_resource",
    "gift": "gift_resource",
}

# Modifier/pipeline/effect id substrings -> action tag. Ordered so the more
# specific substring wins. Most tagging now comes through ``applicability_tags``;
# this map is a fallback for entries that don't tag explicitly.
_ID_KEYWORD_TAGS: tuple[tuple[str, str], ...] = (
    ("anti_block", "anti_block"),
    ("block_break", "anti_block"),
    ("block_mult", "anti_block"),
    ("anti_parry", "anti_parry"),
    ("parry_mult", "anti_parry"),
    ("anti_evasion", "anti_evasion"),
    ("anti_dodge", "anti_evasion"),
    ("dodge_mult", "anti_evasion"),
    ("evasion_mult", "anti_evasion"),
    ("armor_bypass", "armor_bypass"),
    ("armor_ignore", "armor_bypass"),
    ("armor_penetration", "armor_bypass"),
    ("armor_crush", "armor_bypass"),
    ("control", "control"),
    ("stun", "control"),
    ("root", "control"),
    ("knockdown", "control"),
    ("freeze", "control"),
    ("blind", "control"),
    ("concussion", "control"),
    ("bleed", "bleed"),
    ("dot_bleed", "bleed"),
    ("counter", "counter"),
    ("heal", "heal"),
    ("damage", "damage_tag"),
)

# Heuristic keywords identifying healing inside preparation_effects.params.
_HEAL_PARAM_KEYS: tuple[str, ...] = ("heal_max_hp_ratio", "heal_min", "heal_pct", "heal_flat")


@dataclass(frozen=True)
class LegalAction:
    """One scoring candidate for a single (bot, target) pair."""

    action_type: str
    target_id: str
    feint_id: str | None
    cost: dict[str, int] = field(default_factory=dict)
    stamina_cost: int = 0
    tags: frozenset[str] = field(default_factory=frozenset)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"action": self.action_type, "target_id": self.target_id}
        if self.feint_id is not None:
            payload["feint_id"] = self.feint_id
        return payload


def build_legal_actions_for_target(bot: ActorSnapshot, target: ActorSnapshot) -> list[LegalAction]:
    """Enumerate legal actions the bot can take against one target.

    Always emits a plain ``attack``. For each feint currently in
    ``bot.meta.feints.hand`` whose stamina activation cost fits the bot's
    free stamina, a corresponding ``attack + feint`` candidate is added.
    Feints whose stamina exceeds the bot's free stamina are excluded so
    they do not have to be filtered downstream.
    """
    target_id = str(target.meta.id)
    actions: list[LegalAction] = [
        LegalAction(
            action_type=ATTACK_ACTION,
            target_id=target_id,
            feint_id=None,
            cost={},
            stamina_cost=0,
            tags=frozenset({"damage_tag"}),
        )
    ]

    hand = _hand_view(bot)
    if not hand:
        return actions

    available_stamina = max(0, int(bot.meta.stamina or 0))

    for feint_id, cost_dict in hand.items():
        cost = _normalise_cost(cost_dict)
        stamina_cost = FeintService.activation_stamina_cost(cost)
        if stamina_cost > available_stamina:
            continue
        tags = _derive_tags(feint_id, cost)
        actions.append(
            LegalAction(
                action_type=ATTACK_ACTION,
                target_id=target_id,
                feint_id=feint_id,
                cost=cost,
                stamina_cost=stamina_cost,
                tags=tags,
            )
        )
    return actions


def _hand_view(bot: ActorSnapshot) -> dict[str, dict[str, int]]:
    """Read ``bot.meta.feints.hand`` as ``{feint_id: cost_dict}``."""
    feints = bot.meta.feints
    if feints is None:
        return {}
    hand = feints.hand or {}
    return {str(feint_id): _normalise_cost(cost) for feint_id, cost in hand.items() if feint_id}


def _normalise_cost(cost: Any) -> dict[str, int]:
    if not isinstance(cost, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in cost.items():
        try:
            out[str(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return out


def _derive_tags(feint_id: str, cost: dict[str, int]) -> frozenset[str]:
    tags: set[str] = set()
    entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_id)
    if entry is None:
        # Unknown feint: still tag damage so the scorer sees a plain attack-like profile.
        tags.add("damage_tag")
    else:
        technical = entry.technical

        # Designer-authored tags pass through verbatim.
        for tag in technical.applicability_tags or []:
            tags.add(str(tag))

        # Purchase group as an explicit tag for cost-vs-school preferences.
        group = getattr(technical, "purchase_group", "basic") or "basic"
        tags.add(f"group_{group}")

        # Fallback keyword scan over numeric modifiers and pipeline mutations.
        for application in technical.modifier_applications or []:
            tags.update(_keywords_to_tags(str(application.modifier_id)))

        for mutation in technical.pipeline_mutations or []:
            tags.update(_keywords_to_tags(str(mutation.mutation_id)))

        for trigger in technical.triggers or []:
            tags.update(_keywords_to_tags(str(trigger)))

        # Effects on target → debuff signal; effect id substrings → control/bleed/heal.
        for effect in technical.effects or []:
            if not isinstance(effect, dict):
                continue
            effect_id = str(effect.get("id") or "")
            tags.update(_keywords_to_tags(effect_id))
            target_actor = str(effect.get("target_actor") or "target")
            if target_actor == "target":
                tags.add("debuff")

        # Preparation effects on source → self_buff; heal params → heal tag.
        for prep in technical.preparation_effects or []:
            if not isinstance(prep, dict):
                continue
            target_actor = str(prep.get("target_actor") or "source")
            if target_actor == "source":
                tags.add("self_buff")
            params = prep.get("params") or {}
            if isinstance(params, dict) and any(k in params for k in _HEAL_PARAM_KEYS):
                tags.add("heal")
            prep_id = str(prep.get("id") or "")
            tags.update(_keywords_to_tags(prep_id))

        # Shield-guard damage feints (concussion etc.) read as a damage source.
        if (
            getattr(technical, "shield_guard_damage_ratio", 0.0) > 0.0
            or getattr(technical, "shield_guard_damage_min", 0) > 0
        ):
            tags.add("shield_damage")
            tags.add("damage_tag")

        if (technical.target_count or 1) > 1:
            tags.add("multi_target")

    # Tactic-token-derived tags (always evaluated, even for unknown feints).
    for token in cost:
        mapped = _TACTIC_TOKEN_TAGS.get(token)
        if mapped:
            tags.add(mapped)
    return frozenset(tags)


def _keywords_to_tags(text: str) -> set[str]:
    lowered = text.lower()
    tags: set[str] = set()
    for keyword, tag in _ID_KEYWORD_TAGS:
        if keyword in lowered:
            tags.add(tag)
    return tags

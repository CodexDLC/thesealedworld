"""Legal action enumeration for the AI brain.

The exchange action space is the cartesian product of *(target, attack option)*
where an attack option is either a plain ``attack`` or ``attack + feint`` for
each affordable feint sitting in ``bot.meta.feints.hand`` at decision time.
Instant abilities are enumerated separately as optional pre-actions: they do
not consume the target queue and do not replace the exchange.

Exchange tags drive the scorer and are derived **only from the feint's semantic
fields** by :func:`derive_feint_tags`. Instant tags come from ability
``ai_tags``:

- ``applicability_tags`` pass through verbatim.
- ``pipeline_mutations`` produce ``anti_parry`` / ``anti_evasion`` /
  ``anti_block`` / ``armor_bypass`` / ``damage_tag`` according to the
  effective resolved value (override first, then contract default).
- ``effects`` with ``target_actor == "target"`` produce ``debuff`` /
  ``control`` / ``bleed`` / ``dispel_prep``.
- ``preparation_effects`` with ``target_actor == "source"`` produce
  ``self_buff`` plus prep_* and ``heal`` signals.
- ``shield_guard_damage_*`` produces ``shield_damage`` + ``damage_tag``.
- ``purchase_group`` produces ``group_basic`` / ``group_weapon`` /
  ``group_tactical``; ``target_count > 1`` produces ``multi_target``.

Notably absent: the previous derivation read ``cost.tactics`` token slots
and inferred ``anti_evasion`` / ``anti_parry`` / ``anti_block`` / ``damage_tag``
from them. That mixed *resource type* with *effect semantics* and produced
false positives on pure preparation feints. Token costs are now exclusively
a budget signal and contribute no semantic tags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.backend.features.combat.dto.actor import ActorSnapshot  # noqa: TC001
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.ai.feint_tags import derive_feint_tags
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType

ATTACK_ACTION = "attack"
INSTANT_ACTION = "instant"


@dataclass(frozen=True)
class LegalAction:
    """One scoring candidate for a single (bot, target) pair."""

    action_type: str
    target_id: str
    feint_id: str | None
    ability_id: str | None = None
    cost: dict[str, int] = field(default_factory=dict)
    stamina_cost: int = 0
    energy_cost: int = 0
    hp_cost: int = 0
    tags: frozenset[str] = field(default_factory=frozenset)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"action": self.action_type, "target_id": self.target_id}
        if self.feint_id is not None:
            payload["feint_id"] = self.feint_id
        if self.ability_id is not None:
            payload["ability_id"] = self.ability_id
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
        tags = _derive_tags(feint_id)
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


def build_legal_instant_actions_for_target(bot: ActorSnapshot, target: ActorSnapshot) -> list[LegalAction]:
    """Enumerate affordable instant abilities that may precede an exchange.

    Instant abilities do not consume the target queue and do not replace the
    exchange. They are scored as optional pre-actions, so this function returns
    only concrete affordable abilities; the brain supplies the "skip instant"
    baseline separately.
    """
    actions: list[LegalAction] = []
    known_abilities = [str(ability_id) for ability_id in bot.loadout.known_abilities if ability_id]
    if not known_abilities:
        return actions

    for ability_id in known_abilities:
        entry = CombatCatalogIntegrator.get_ability_catalog_entry(ability_id)
        if entry is None:
            continue
        ability = entry.technical
        if not _ability_cost_affordable(bot, ability.cost):
            continue
        target_id = _ability_target_id(bot, target, ability.target)
        if target_id is None:
            continue
        actions.append(
            LegalAction(
                action_type=INSTANT_ACTION,
                target_id=target_id,
                feint_id=None,
                ability_id=ability.ability_id,
                cost=_ability_token_cost(ability.cost),
                energy_cost=max(0, int(ability.cost.energy or 0)),
                hp_cost=max(0, int(ability.cost.hp or 0)),
                tags=frozenset(_ability_tags(ability.ai_tags)),
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


def _ability_cost_affordable(bot: ActorSnapshot, cost: Any) -> bool:
    if int(bot.meta.en or 0) < max(0, int(cost.energy or 0)):
        return False
    if int(bot.meta.hp or 0) < max(0, int(cost.hp or 0)):
        return False
    token_cost = _ability_token_cost(cost)
    return all(int(bot.meta.tokens.get(token, 0) or 0) >= amount for token, amount in token_cost.items())


def _ability_token_cost(cost: Any) -> dict[str, int]:
    token_cost = _normalise_cost(getattr(cost, "tokens", {}) or {})
    gift_tokens = max(0, int(getattr(cost, "gift_tokens", 0) or 0))
    if gift_tokens:
        token_cost["gift"] = token_cost.get("gift", 0) + gift_tokens
    return token_cost


def _ability_target_id(bot: ActorSnapshot, target: ActorSnapshot, target_type: TargetType) -> str | None:
    if target_type == TargetType.SELF:
        return str(bot.meta.id)
    if target_type in {TargetType.SINGLE_ENEMY, TargetType.LOWEST_HP_ENEMY, TargetType.RANDOM_ENEMY}:
        return str(target.meta.id)
    if target_type == TargetType.SINGLE_ALLY:
        return str(bot.meta.id)
    return None


def _ability_tags(tags: list[str]) -> set[str]:
    out = {str(tag) for tag in tags if tag}
    if "damage" in out:
        out.add("damage_tag")
    if "anti_defense" in out:
        out.update({"anti_evasion", "anti_parry", "anti_block"})
    return out


def _derive_tags(feint_id: str) -> frozenset[str]:
    """Resolve a feint's catalog entry and produce its semantic action tags.

    Unknown feints fall back to ``{"damage_tag"}`` so a missing catalog
    lookup never demotes a feint below the basic attack baseline.
    """
    entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_id)
    if entry is None:
        return frozenset({"damage_tag"})
    return derive_feint_tags(entry, feint_id)

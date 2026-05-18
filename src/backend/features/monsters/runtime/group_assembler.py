from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.monsters.resources import get_family_config

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.monsters.dto.generation import GeneratedMonster


ENCOUNTER_BALANCE_CONFIG: dict[str, Any] = {
    "global": {
        "budget_multiplier": 1.0,
        "danger_budget_bonus_per_point": 0.25,
        "budget_min": 1.0,
        "budget_max": 999_999.0,
        "budget_soft_overflow_pct": 0.0,
        "allow_single_over_budget": True,
        "allow_repeated_members": True,
        "fill_minion_slots_before_upgrades": True,
        "randomize_candidates": True,
    },
    "action_economy": {
        "enabled": True,
        "by_count": {
            1: 1.0,
            2: 1.0,
            3: 1.08,
            4: 1.14,
            5: 1.20,
            6: 1.27,
            8: 1.38,
            10: 1.50,
        },
    },
    "role_weights": {
        "minion": 1.0,
        "veteran": 1.0,
        "elite": 1.0,
        "boss": 1.0,
    },
    "organizations": {
        "swarm": {
            "start_minions": 10,
            "min_units": 4,
            "max_units": 10,
            "max_veterans": 4,
            "max_elites": 2,
            "boss_allowed": False,
            "upgrade_order": ["veteran", "elite", "boss"],
        },
        "horde": {
            "start_minions": 5,
            "min_units": 3,
            "max_units": 8,
            "max_veterans": 3,
            "max_elites": 1,
            "boss_allowed": False,
            "upgrade_order": ["veteran", "elite", "boss"],
        },
        "pack": {
            "start_minions": 2,
            "min_units": 2,
            "max_units": 5,
            "max_veterans": 3,
            "max_elites": 1,
            "boss_allowed": False,
            "upgrade_order": ["veteran", "elite", "boss"],
        },
        "gang": {
            "start_minions": 3,
            "min_units": 2,
            "max_units": 6,
            "max_veterans": 3,
            "max_elites": 2,
            "boss_allowed": False,
            "upgrade_order": ["veteran", "elite", "boss"],
        },
        "solitary": {
            "start_minions": 1,
            "min_units": 1,
            "max_units": 1,
            "max_veterans": 1,
            "max_elites": 1,
            "boss_allowed": True,
            "upgrade_order": ["veteran", "elite", "boss"],
        },
        "clan": {
            "start_minions": 4,
            "min_units": 3,
            "max_units": 7,
            "max_veterans": 3,
            "max_elites": 2,
            "boss_allowed": False,
            "upgrade_order": ["veteran", "elite", "boss"],
        },
        "legion": {
            "start_minions": 6,
            "min_units": 4,
            "max_units": 10,
            "max_veterans": 4,
            "max_elites": 2,
            "boss_allowed": False,
            "upgrade_order": ["veteran", "elite", "boss"],
        },
    },
}

ROLE_ORDER = {"minion": 1, "veteran": 2, "elite": 3, "boss": 4}
LOWER_ROLE_ORDER = {
    "veteran": ("minion",),
    "elite": ("veteran", "minion"),
    "boss": ("elite", "veteran", "minion"),
}


@dataclass(frozen=True, slots=True)
class MonsterGroupAssembly:
    members: list[GeneratedMonster]
    target_budget: float
    adjusted_budget: float
    total_power: int


class MonsterGroupAssembler:
    """Select generated monsters by gear-score budget and organization rules."""

    def __init__(self, config: dict[str, Any] | None = None, rng: random.Random | None = None) -> None:
        self.config = deepcopy(config or ENCOUNTER_BALANCE_CONFIG)
        self._rng = rng or random.Random()  # nosec B311

    def assemble(
        self,
        members: Sequence[GeneratedMonster],
        *,
        budget: float,
        tier: int,
        danger: float,
        force_single_family: bool = True,
    ) -> MonsterGroupAssembly:
        del force_single_family  # Current caller already passes members from one clan.
        target_budget = self._target_budget(budget)
        adjusted_budget = self.adjust_budget(target_budget, tier=tier, danger=danger)
        candidates = self._sorted_candidates(members)
        if not candidates:
            return MonsterGroupAssembly([], target_budget, adjusted_budget, 0)

        organization = self._organization_type(candidates)
        rule = self._organization_rule(organization)
        selected = self._select_by_rule(candidates, adjusted_budget, rule)
        total_power = sum(self._member_power(member) for member in selected)
        return MonsterGroupAssembly(
            members=selected,
            target_budget=target_budget,
            adjusted_budget=adjusted_budget,
            total_power=total_power,
        )

    def adjust_budget(self, budget: float, *, tier: int, danger: float) -> float:
        del tier
        global_config = self.config["global"]
        danger_bonus = min(1.0, max(0.0, danger)) * float(global_config["danger_budget_bonus_per_point"])
        adjusted = budget * (1.0 + danger_bonus)
        return round(self._clamp_budget(adjusted), 2)

    def _select_by_rule(
        self,
        candidates: list[GeneratedMonster],
        budget: float,
        rule: dict[str, Any],
    ) -> list[GeneratedMonster]:
        if int(rule["max_units"]) == 1:
            return [self._best_single(candidates, budget, rule)]

        selected: list[GeneratedMonster] = []
        start_minions = self._start_minion_target(candidates, rule)

        self._fill_role(selected, candidates, "minion", start_minions, budget, rule)

        self._fill_min_units(selected, candidates, budget, rule)
        self._upgrade_group(selected, candidates, budget, rule)
        return sorted(
            selected,
            key=lambda member: (ROLE_ORDER.get(member.role, 9), self._member_power(member), member.variant_key),
        )

    def _start_minion_target(
        self,
        candidates: list[GeneratedMonster],
        rule: dict[str, Any],
    ) -> int:
        max_units = int(rule["max_units"])
        if bool(self.config["global"]["fill_minion_slots_before_upgrades"]):
            return max_units
        unique_minions = len({member.variant_key for member in candidates if member.role == "minion"})
        return min(max(int(rule["start_minions"]), unique_minions), max_units)

    def _best_single(
        self,
        candidates: list[GeneratedMonster],
        budget: float,
        rule: dict[str, Any],
    ) -> GeneratedMonster:
        allowed_roles = [member for member in candidates if member.role != "boss" or bool(rule["boss_allowed"])]
        pool = allowed_roles or candidates
        return min(pool, key=lambda member: _single_score(self._member_power(member), budget))

    def _fill_role(
        self,
        selected: list[GeneratedMonster],
        candidates: list[GeneratedMonster],
        role: str,
        target_count: int,
        budget: float,
        rule: dict[str, Any],
    ) -> None:
        while len(selected) < target_count:
            added = self._try_add_from_pool(selected, self._role_candidates(candidates, role), budget, rule)
            if not added:
                break

    def _fill_min_units(
        self,
        selected: list[GeneratedMonster],
        candidates: list[GeneratedMonster],
        budget: float,
        rule: dict[str, Any],
    ) -> None:
        while len(selected) < int(rule["min_units"]):
            added = self._try_add_from_pool(selected, candidates, budget, rule)
            if not added:
                break

    def _upgrade_group(
        self,
        selected: list[GeneratedMonster],
        candidates: list[GeneratedMonster],
        budget: float,
        rule: dict[str, Any],
    ) -> None:
        for role in rule["upgrade_order"]:
            if role == "boss" and not bool(rule["boss_allowed"]):
                continue
            while self._role_count(selected, role) < self._role_cap(rule, role):
                upgraded = self._try_upgrade_role(selected, candidates, budget, rule, role)
                if not upgraded:
                    break

    def _try_upgrade_role(
        self,
        selected: list[GeneratedMonster],
        candidates: list[GeneratedMonster],
        budget: float,
        rule: dict[str, Any],
        role: str,
    ) -> bool:
        for candidate in self._role_candidates(candidates, role):
            replacement = self._replacement_for(selected, role)
            if replacement is not None and self._fits_replacement(selected, replacement, candidate, budget):
                selected.remove(replacement)
                selected.append(candidate)
                return True
            if replacement is None and self._try_add(selected, candidate, budget, rule):
                return True
        return False

    def _try_add_from_pool(
        self,
        selected: list[GeneratedMonster],
        candidates: list[GeneratedMonster],
        budget: float,
        rule: dict[str, Any],
    ) -> bool:
        unique_candidates = [member for member in candidates if member not in selected]
        repeated_candidates = [member for member in candidates if member in selected]
        fitting_unique = [member for member in unique_candidates if self._fits_budget([*selected, member], budget)]
        fitting_repeated = [member for member in repeated_candidates if self._fits_budget([*selected, member], budget)]
        overflow_unique = [member for member in unique_candidates if member not in fitting_unique]
        overflow_repeated = [member for member in repeated_candidates if member not in fitting_repeated]
        pool = [*fitting_unique, *fitting_repeated, *overflow_unique, *overflow_repeated]
        return any(self._try_add(selected, member, budget, rule) for member in pool)

    def _try_add(
        self,
        selected: list[GeneratedMonster],
        member: GeneratedMonster,
        budget: float,
        rule: dict[str, Any],
    ) -> bool:
        if not bool(self.config["global"]["allow_repeated_members"]) and member in selected:
            return False
        if len(selected) >= int(rule["max_units"]):
            return False
        if member.role == "boss" and not bool(rule["boss_allowed"]):
            return False
        if self._role_count(selected, member.role) >= self._role_cap(rule, member.role):
            return False
        next_members = [*selected, member]
        if not self._fits_budget(next_members, budget):
            allow_single = bool(self.config["global"]["allow_single_over_budget"])
            if selected or not allow_single:
                return False
        selected.append(member)
        return True

    def _fits_replacement(
        self,
        selected: list[GeneratedMonster],
        old_member: GeneratedMonster,
        new_member: GeneratedMonster,
        budget: float,
    ) -> bool:
        next_members = [member for member in selected if member is not old_member]
        next_members.append(new_member)
        return self._fits_budget(next_members, budget)

    def _fits_budget(self, members: list[GeneratedMonster], budget: float) -> bool:
        soft_overflow = float(self.config["global"]["budget_soft_overflow_pct"])
        allowed = budget * (1.0 + max(0.0, soft_overflow))
        return self._effective_total(members) <= allowed

    def _effective_total(self, members: list[GeneratedMonster]) -> float:
        total = sum(self._member_power(member) for member in members)
        return round(total * self._action_economy_multiplier(len(members)), 2)

    def _member_power(self, member: GeneratedMonster) -> int:
        balance = _balance(member)
        raw_score = balance.get("gear_score")
        if raw_score is None:
            return 0
        weight = float(self.config["role_weights"].get(member.role, 1.0))
        return max(1, int(round(float(raw_score) * weight)))

    def _sorted_candidates(self, members: Sequence[GeneratedMonster]) -> list[GeneratedMonster]:
        candidates = [member for member in members if self._member_power(member) > 0]
        return sorted(
            candidates,
            key=lambda member: (ROLE_ORDER.get(member.role, 9), self._member_power(member), member.variant_key),
        )

    def _organization_type(self, candidates: list[GeneratedMonster]) -> str:
        balance = _balance(candidates[0])
        organization = str(balance.get("organization_type") or "")
        if organization in self.config["organizations"]:
            return organization
        family_id = candidates[0].family_id
        family = get_family_config(family_id) if family_id else None
        if family is not None and family.organization_type in self.config["organizations"]:
            return family.organization_type
        return "solitary"

    def _organization_rule(self, organization: str) -> dict[str, Any]:
        return dict(self.config["organizations"].get(organization) or self.config["organizations"]["solitary"])

    def _role_candidates(
        self,
        candidates: list[GeneratedMonster],
        role: str,
    ) -> list[GeneratedMonster]:
        return self._ordered_candidates([member for member in candidates if member.role == role])

    def _ordered_candidates(self, candidates: list[GeneratedMonster]) -> list[GeneratedMonster]:
        ordered = list(candidates)
        if bool(self.config["global"]["randomize_candidates"]):
            self._rng.shuffle(ordered)
            return ordered
        return sorted(
            ordered, key=lambda member: (ROLE_ORDER.get(member.role, 9), self._member_power(member), member.variant_key)
        )

    @staticmethod
    def _replacement_for(selected: list[GeneratedMonster], target_role: str) -> GeneratedMonster | None:
        for role in LOWER_ROLE_ORDER.get(target_role, ()):
            matching = [member for member in selected if member.role == role]
            if matching:
                return sorted(matching, key=lambda member: (ROLE_ORDER.get(member.role, 9), member.variant_key))[0]
        return None

    @staticmethod
    def _role_count(members: list[GeneratedMonster], role: str) -> int:
        return sum(1 for member in members if member.role == role)

    @staticmethod
    def _role_cap(rule: dict[str, Any], role: str) -> int:
        if role == "minion":
            return int(rule["max_units"])
        if role == "veteran":
            return int(rule["max_veterans"])
        if role == "elite":
            return int(rule["max_elites"])
        if role == "boss":
            return 1 if bool(rule["boss_allowed"]) else 0
        return 0

    def _action_economy_multiplier(self, count: int) -> float:
        if not self.config["action_economy"]["enabled"] or count <= 0:
            return 1.0
        table = self.config["action_economy"]["by_count"]
        threshold = max((int(key) for key in table if int(key) <= count), default=1)
        return float(table[threshold])

    def _target_budget(self, budget: float) -> float:
        multiplier = float(self.config["global"]["budget_multiplier"])
        return round(self._clamp_budget(float(budget) * multiplier), 2)

    def _clamp_budget(self, budget: float) -> float:
        global_config = self.config["global"]
        return min(float(global_config["budget_max"]), max(float(global_config["budget_min"]), budget))


def _balance(member: GeneratedMonster) -> dict[str, Any]:
    raw_balance = (member.generation_meta or {}).get("balance")
    return dict(raw_balance) if isinstance(raw_balance, dict) else {}


def _single_score(power: int, budget: float) -> tuple[int, float, int]:
    overshoot = 1 if power > budget else 0
    return overshoot, abs(power - budget), -power


__all__ = ["ENCOUNTER_BALANCE_CONFIG", "MonsterGroupAssembler", "MonsterGroupAssembly"]

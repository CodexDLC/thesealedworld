"""Family pressure simulations for starter imprint balance probes."""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass, field
from statistics import mean
from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto import ActorLoadoutDTO, ActorMetaDTO, ActorRawDTO, ActorSnapshot, FeintHandDTO
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine
from src.backend.features.combat.runtime.simulation.factory import InMemoryBattleFactory
from src.backend.features.combat.runtime.simulation.simulator import InMemoryCombatSimulator
from src.backend.features.combat.runtime.simulation.starting_imprint_actors import (
    STARTER_SKILL_PROFILE_BASELINE,
    StartingImprintSimulationActorBuilder,
)
from src.backend.features.combat.runtime.simulation.state import InMemoryBattleLimits
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder
from src.backend.features.monsters.runtime.group_assembler import ENCOUNTER_BALANCE_CONFIG
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.generation import GeneratedMonster

ROLE_ORDER = ("minion", "veteran", "elite", "boss")
DEFAULT_COMBAT_TOKENS = {"hit": 4, "crit": 4, "block": 4, "parry": 4, "dodge": 4, "tempo": 4, "blood": 2, "gift": 2}
FamilyPressureProgressCallback = Callable[["FamilyPressureReport"], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class FamilyPressureComposition:
    """A concrete role-count scenario for one family."""

    key: str
    role_counts: dict[str, int]
    grade: str = "light"


@dataclass(frozen=True, slots=True)
class FamilyPressureTrial:
    winner: str
    rounds: int
    player_hp: int
    completion_reason: str


@dataclass(frozen=True, slots=True)
class FamilyPressureCompositionReport:
    composition: FamilyPressureComposition
    member_variants: list[str]
    member_roles: list[str]
    member_gear_scores: list[int]
    raw_gear_score: int
    effective_gear_score: float
    effective_ratio: float
    trials: int
    player_wins: int
    monster_wins: int
    draws: int
    player_win_rate: float
    avg_player_hp: float
    avg_rounds: float
    first_player_death_trial: int | None


@dataclass(frozen=True, slots=True)
class FamilyPressureReport:
    family_id: str
    imprint_key: str
    imprint_title: str
    player_gear_score: int
    player_start_hp: int
    trials_per_composition: int
    reports: list[FamilyPressureCompositionReport] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FamilyPressureConfig:
    trials_per_composition: int = 5
    max_rounds: int = 80
    max_minions: int = 6
    max_scenarios: int = 24
    skill_profile: str = STARTER_SKILL_PROFILE_BASELINE


class FamilyPressureSimulator:
    """Runs one starter imprint against a progressive family roster ladder."""

    def __init__(
        self,
        *,
        imprint_builder: StartingImprintSimulationActorBuilder | None = None,
        monster_builder: MonsterCombatActorInputBuilder | None = None,
        gear_scores: MonsterGearScoreService | None = None,
        simulator: InMemoryCombatSimulator | None = None,
    ) -> None:
        self.imprint_builder = imprint_builder or StartingImprintSimulationActorBuilder()
        self.monster_builder = monster_builder or MonsterCombatActorInputBuilder()
        self.gear_scores = gear_scores or MonsterGearScoreService(self.monster_builder)
        self.simulator = simulator or InMemoryCombatSimulator()

    async def run(
        self,
        *,
        family_id: str,
        imprint_key: str,
        members: list[GeneratedMonster],
        seed: int = 0,
        config: FamilyPressureConfig | None = None,
        progress: FamilyPressureProgressCallback | None = None,
    ) -> FamilyPressureReport:
        cfg = config or FamilyPressureConfig()
        members = [member for member in members if member.family_id == family_id]
        if not members:
            raise ValueError(f"No generated monsters found for family: {family_id}")
        self.gear_scores.refresh_stale_monster_scores(members)

        player_reference = self.imprint_builder.build_actor(
            imprint_key,
            actor_id="pressure_player_reference",
            team="blue",
            skill_profile=cfg.skill_profile,
        )
        player_gs = int(player_reference.participant["gear_score"]["total"])
        player_start_hp = int(player_reference.actor.meta.max_hp)
        compositions = build_family_pressure_compositions(
            family_id,
            members=members,
            max_minions=cfg.max_minions,
            max_scenarios=cfg.max_scenarios,
        )
        reports: list[FamilyPressureCompositionReport] = []
        for scenario_index, composition in enumerate(compositions):
            selected_members = select_members_for_composition(members, composition)
            if not selected_members:
                continue

            async def publish_partial(partial: FamilyPressureCompositionReport) -> None:
                if progress is None:
                    return
                await progress(
                    FamilyPressureReport(
                        family_id=family_id,
                        imprint_key=imprint_key,
                        imprint_title=str(player_reference.participant.get("imprint_title") or imprint_key),
                        player_gear_score=player_gs,
                        player_start_hp=player_start_hp,
                        trials_per_composition=cfg.trials_per_composition,
                        reports=[*reports, partial],
                    )
                )

            reports.append(
                await self._run_composition(
                    composition=composition,
                    selected_members=selected_members,
                    imprint_key=imprint_key,
                    seed=seed + scenario_index * 10_000,
                    config=cfg,
                    player_gear_score=player_gs,
                    progress=publish_partial,
                )
            )
        return FamilyPressureReport(
            family_id=family_id,
            imprint_key=imprint_key,
            imprint_title=str(player_reference.participant.get("imprint_title") or imprint_key),
            player_gear_score=player_gs,
            player_start_hp=player_start_hp,
            trials_per_composition=cfg.trials_per_composition,
            reports=reports,
        )

    async def _run_composition(
        self,
        *,
        composition: FamilyPressureComposition,
        selected_members: list[GeneratedMonster],
        imprint_key: str,
        seed: int,
        config: FamilyPressureConfig,
        player_gear_score: int,
        progress: Callable[[FamilyPressureCompositionReport], Awaitable[None]] | None = None,
    ) -> FamilyPressureCompositionReport:
        trials: list[FamilyPressureTrial] = []
        member_scores = [monster_gear_score(member) for member in selected_members]
        raw_score = sum(member_scores)
        effective_score = round(raw_score * action_economy_multiplier(len(selected_members)), 2)
        for trial_index in range(config.trials_per_composition):
            random.seed(seed + trial_index)
            actors = self._build_trial_actors(
                selected_members,
                imprint_key=imprint_key,
                trial_index=trial_index,
                skill_profile=config.skill_profile,
            )
            state = InMemoryBattleFactory.from_actors(
                actors,
                session_id=f"family-pressure-{imprint_key}-{composition.key}-{trial_index}",
                limits=InMemoryBattleLimits(
                    max_rounds=config.max_rounds,
                    candidate_limit=5,
                    max_actions_per_round=200,
                    force_unanswered_exchange=True,
                ),
                seed=seed + trial_index,
                battle_type="simulation",
                location_id="family-pressure",
            )
            result = await self.simulator.run(state)
            trials.append(
                FamilyPressureTrial(
                    winner=result.winner,
                    rounds=result.rounds_completed,
                    player_hp=int(result.final_hp_by_actor.get("player", 0)),
                    completion_reason=result.completion_reason,
                )
            )
            if progress is not None:
                await progress(
                    _composition_report_from_trials(
                        composition=composition,
                        selected_members=selected_members,
                        member_scores=member_scores,
                        raw_score=raw_score,
                        effective_score=effective_score,
                        player_gear_score=player_gear_score,
                        trials=trials,
                    )
                )
        return _composition_report_from_trials(
            composition=composition,
            selected_members=selected_members,
            member_scores=member_scores,
            raw_score=raw_score,
            effective_score=effective_score,
            player_gear_score=player_gear_score,
            trials=trials,
        )

    def _build_trial_actors(
        self,
        selected_members: list[GeneratedMonster],
        *,
        imprint_key: str,
        trial_index: int,
        skill_profile: str,
    ) -> list[ActorSnapshot]:
        player = self.imprint_builder.build_actor(
            imprint_key,
            actor_id="player",
            team="blue",
            skill_profile=skill_profile,
        ).actor
        enemies = [
            self._monster_actor(member, actor_id=f"monster_{index}", team="red")
            for index, member in enumerate(selected_members, start=1)
        ]
        for actor in [player, *enemies]:
            actor.metrics["family_pressure_trial"] = float(trial_index)
        return [player, *enemies]

    def _monster_actor(self, monster: GeneratedMonster, *, actor_id: str, team: str) -> ActorSnapshot:
        source = self.monster_builder.build_snapshot(monster)
        meta = dict(source.get("meta") or {})
        status = dict(source.get("status") or {})
        combat = dict(source.get("combat") or {})
        raw = dict(combat.get("math_model") or {})
        loadout = dict(combat.get("loadout") or {})
        known_feints = [str(feint_id) for feint_id in loadout.get("known_feints") or []]
        actor = ActorSnapshot(
            meta=ActorMetaDTO(
                id=actor_id,
                name=str(meta.get("name") or monster.name_ru or actor_id),
                type="monster",
                team=team,
                template_id=str(monster.variant_key),
                is_ai=True,
                archetype=str(meta.get("archetype") or "unknown"),
                ai_archetype=str(meta.get("ai_archetype") or "balanced"),
                hp=_vital(status, "hp", default=1),
                max_hp=_vital_max(status, "hp", default=1),
                en=_vital(status, "energy", default=1),
                max_en=_vital_max(status, "energy", default=1),
                stamina=_vital(status, "stamina", default=1),
                max_stamina=_vital_max(status, "stamina", default=1),
                tokens=dict(DEFAULT_COMBAT_TOKENS),
                feints=FeintHandDTO(arsenal=known_feints, hand={}),
            ),
            raw=ActorRawDTO(
                attributes=deepcopy(raw.get("attributes") or {}),
                modifiers=deepcopy(raw.get("modifiers") or {}),
                pipeline=deepcopy(raw.get("pipeline") or {}),
                rules=deepcopy(raw.get("rules") or {}),
            ),
            skills=deepcopy(combat.get("skills") or {}),
            loadout=ActorLoadoutDTO.model_validate(loadout),
        )
        StatsEngine.ensure_stats(actor)
        _hydrate_resources_from_stats(actor)
        FeintService.refill_hand(actor.meta, hand_size=3)
        return actor


def build_family_pressure_compositions(
    family_id: str,
    *,
    members: list[GeneratedMonster],
    max_minions: int = 6,
    max_scenarios: int = 24,
) -> list[FamilyPressureComposition]:
    roles_available = {member.role for member in members}
    organization = _organization_type(family_id)
    rule = dict(ENCOUNTER_BALANCE_CONFIG["organizations"].get(organization) or {})
    max_units = max(1, int(rule.get("max_units") or max_minions))
    max_units = min(max_units, max(1, int(max_minions)))

    rows: list[FamilyPressureComposition] = []
    minion_start = _family_pressure_minion_start(organization, rule, max_units)
    for count in range(minion_start, max_units + 1):
        if "minion" in roles_available:
            rows.append(_composition({"minion": count}, grade="medium" if count >= max_units else "light"))
    if "veteran" in roles_available:
        for veterans in range(1, max_units + 1):
            rows.append(
                _composition(
                    {"minion": max_units - veterans, "veteran": veterans},
                    grade="medium" if veterans <= max_units // 2 else "hard",
                )
            )
    if "elite" in roles_available:
        if "veteran" in roles_available:
            for elites in range(1, max_units + 1):
                rows.append(_composition({"veteran": max_units - elites, "elite": elites}, grade="hard"))
        elif "minion" in roles_available:
            for elites in range(1, max_units + 1):
                rows.append(_composition({"minion": max_units - elites, "elite": elites}, grade="hard"))
    if "minion" in roles_available and "elite" in roles_available:
        rows.append(_composition({"minion": min(2, max_units - 1), "elite": 1}, grade="hard"))
    if "minion" in roles_available and "boss" in roles_available:
        rows.append(_composition({"minion": min(2, max_units - 1), "boss": 1}, grade="boss_probe"))

    return _unique_compositions(rows)[: max(1, int(max_scenarios))]


def select_members_for_composition(
    members: list[GeneratedMonster],
    composition: FamilyPressureComposition,
) -> list[GeneratedMonster]:
    selected: list[GeneratedMonster] = []
    by_role = {
        role: sorted(
            [member for member in members if member.role == role],
            key=lambda member: (monster_gear_score(member), member.variant_key, str(member.id)),
        )
        for role in ROLE_ORDER
    }
    for role in ROLE_ORDER:
        pool = by_role.get(role) or []
        count = int(composition.role_counts.get(role, 0))
        if count and not pool:
            return []
        for index in range(count):
            selected.append(pool[index % len(pool)])
    return selected


def _composition_report_from_trials(
    *,
    composition: FamilyPressureComposition,
    selected_members: list[GeneratedMonster],
    member_scores: list[int],
    raw_score: int,
    effective_score: float,
    player_gear_score: int,
    trials: list[FamilyPressureTrial],
) -> FamilyPressureCompositionReport:
    player_wins = sum(1 for trial in trials if trial.winner == "blue")
    monster_wins = sum(1 for trial in trials if trial.winner == "red")
    draws = len(trials) - player_wins - monster_wins
    deaths = [index + 1 for index, trial in enumerate(trials) if trial.player_hp <= 0]
    return FamilyPressureCompositionReport(
        composition=composition,
        member_variants=[member.variant_key for member in selected_members],
        member_roles=[member.role for member in selected_members],
        member_gear_scores=member_scores,
        raw_gear_score=raw_score,
        effective_gear_score=effective_score,
        effective_ratio=round(effective_score / max(1, player_gear_score), 3),
        trials=len(trials),
        player_wins=player_wins,
        monster_wins=monster_wins,
        draws=draws,
        player_win_rate=round(player_wins / max(1, len(trials)), 3),
        avg_player_hp=round(mean([trial.player_hp for trial in trials]), 2) if trials else 0.0,
        avg_rounds=round(mean([trial.rounds for trial in trials]), 2) if trials else 0.0,
        first_player_death_trial=deaths[0] if deaths else None,
    )


def monster_gear_score(monster: GeneratedMonster) -> int:
    balance = dict((monster.generation_meta or {}).get("balance") or {})
    try:
        return int(balance["gear_score"])
    except (KeyError, TypeError, ValueError):
        return 0


def action_economy_multiplier(count: int) -> float:
    config = ENCOUNTER_BALANCE_CONFIG["action_economy"]
    if not config["enabled"] or count <= 0:
        return 1.0
    table = config["by_count"]
    threshold = max((int(key) for key in table if int(key) <= count), default=1)
    return float(table[threshold])


def format_family_pressure_report(report: FamilyPressureReport) -> str:
    lines = [
        f"# Family pressure: {report.imprint_key} vs {report.family_id}",
        "",
        f"player_gs={report.player_gear_score} player_hp={report.player_start_hp} trials={report.trials_per_composition}",
        "",
        "| composition | raw_gs | eff_gs | ratio | winrate | W/L/D | avg_hp | avg_rounds | variants |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.reports:
        composition = " + ".join(f"{count}x {role}" for role, count in row.composition.role_counts.items() if count > 0)
        variants = ", ".join(row.member_variants)
        lines.append(
            "| "
            f"{composition} | "
            f"{row.raw_gear_score} | "
            f"{row.effective_gear_score:.2f} | "
            f"{row.effective_ratio:.3f} | "
            f"{row.player_win_rate:.3f} | "
            f"{row.player_wins}/{row.monster_wins}/{row.draws} | "
            f"{row.avg_player_hp:.2f} | "
            f"{row.avg_rounds:.2f} | "
            f"{variants} |"
        )
    return "\n".join(lines)


def _composition(role_counts: dict[str, int], *, grade: str) -> FamilyPressureComposition:
    normalized = {role: int(role_counts.get(role, 0)) for role in ROLE_ORDER if int(role_counts.get(role, 0)) > 0}
    key = "_".join(f"{role[0]}{count}" for role, count in normalized.items())
    return FamilyPressureComposition(key=key, role_counts=normalized, grade=grade)


def _unique_compositions(rows: list[FamilyPressureComposition]) -> list[FamilyPressureComposition]:
    unique: dict[str, FamilyPressureComposition] = {}
    for row in rows:
        unique.setdefault(row.key, row)
    return list(unique.values())


def _family_pressure_minion_start(organization: str, rule: dict[str, Any], max_units: int) -> int:
    if organization == "swarm":
        return min(3, max_units)
    configured_min = int(rule.get("min_units") or 1)
    return min(max(1, configured_min), max_units)


def _composition_sort_key(row: FamilyPressureComposition) -> tuple[int, int, int, int]:
    counts = row.role_counts
    total = sum(counts.values())
    if counts.get("minion", 0) == total:
        return (0, total, 0, 0)
    return (1, total, counts.get("elite", 0), counts.get("veteran", 0))


def _organization_type(family_id: str) -> str:
    family = get_family_config(family_id)
    if family is None:
        return "solitary"
    return str(family.organization_type or "solitary")


def _vital(status: dict[str, Any], key: str, *, default: int) -> int:
    raw = status.get(key)
    data = raw if isinstance(raw, dict) else {}
    return _int(data.get("cur", data.get("current", default)), default=default)


def _vital_max(status: dict[str, Any], key: str, *, default: int) -> int:
    raw = status.get(key)
    data = raw if isinstance(raw, dict) else {}
    return max(_vital(status, key, default=default), _int(data.get("max", default), default=default))


def _int(value: Any, *, default: int) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _hydrate_resources_from_stats(actor: ActorSnapshot) -> None:
    if actor.stats is None:
        return
    mods = actor.stats.mods
    actor.meta.max_hp = max(actor.meta.max_hp, _int(mods.hp, default=actor.meta.max_hp))
    actor.meta.hp = max(1, min(actor.meta.hp or actor.meta.max_hp, actor.meta.max_hp))
    actor.meta.max_en = max(actor.meta.max_en, _int(mods.en, default=actor.meta.max_en))
    actor.meta.en = max(1, min(actor.meta.en or actor.meta.max_en, actor.meta.max_en))
    actor.meta.max_stamina = max(actor.meta.max_stamina, _int(mods.stamina, default=actor.meta.max_stamina))
    actor.meta.stamina = max(1, min(actor.meta.stamina or actor.meta.max_stamina, actor.meta.max_stamina))


__all__ = [
    "FamilyPressureComposition",
    "FamilyPressureCompositionReport",
    "FamilyPressureConfig",
    "FamilyPressureReport",
    "FamilyPressureSimulator",
    "FamilyPressureTrial",
    "build_family_pressure_compositions",
    "format_family_pressure_report",
    "select_members_for_composition",
]

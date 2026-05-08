from __future__ import annotations

import argparse
import asyncio
import copy
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import redis.asyncio as redis

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backend.config.settings import settings  # noqa: E402
from src.backend.features.combat.dto import CombatMoveDTO, ExchangePayload  # noqa: E402
from src.backend.features.combat.integrations import CombatSessionIntegration  # noqa: E402
from src.backend.features.combat.runtime.engine.context_builder import ContextBuilder  # noqa: E402
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine  # noqa: E402
from src.backend.features.combat.runtime.processors.executor import CombatExecutor  # noqa: E402

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorSnapshot, ActorStats


class RedisAdapter:
    def __init__(self, client: redis.Redis) -> None:
        self.redis_client = client
        self.json_module = client.json()


@dataclass
class ProbeStats:
    attempts: int = 0
    hits: int = 0
    misses: int = 0
    crits: int = 0
    dodges: int = 0
    parries: int = 0
    blocks: int = 0
    skips: int = 0
    deaths: int = 0
    damage: list[int] | None = None

    def record(self, result: Any) -> None:
        self.attempts += 1
        self.hits += int(result.is_hit)
        self.misses += int(result.is_miss)
        self.crits += int(result.is_crit)
        self.dodges += int(result.is_dodged)
        self.parries += int(result.is_parried)
        self.blocks += int(result.is_blocked)
        self.skips += int(bool(result.skip_reason))
        self.deaths += int(any(event.type == "DEATH" for event in result.events))
        if self.damage is None:
            self.damage = []
        if result.damage_final:
            self.damage.append(int(result.damage_final))

    def summary(self) -> dict[str, Any]:
        damage = self.damage or []
        return {
            "attempts": self.attempts,
            "hit_rate": _rate(self.hits, self.attempts),
            "miss_rate": _rate(self.misses, self.attempts),
            "crit_rate": _rate(self.crits, self.attempts),
            "dodge_rate": _rate(self.dodges, self.attempts),
            "parry_rate": _rate(self.parries, self.attempts),
            "block_rate": _rate(self.blocks, self.attempts),
            "skip_rate": _rate(self.skips, self.attempts),
            "death_rate": _rate(self.deaths, self.attempts),
            "damage": {
                "count": len(damage),
                "avg": round(statistics.mean(damage), 4) if damage else 0,
                "min": min(damage) if damage else 0,
                "max": max(damage) if damage else 0,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe observed combat chances from a live combat Redis session.")
    parser.add_argument("session_id", help="Combat session id, e.g. 3d9a0390-7507-4b86-b0d5-51604cfd2677.")
    parser.add_argument("--source", required=True, help="Attacker actor id in combat session.")
    parser.add_argument("--target", required=True, help="Target actor id in combat session.")
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--hp", type=int, default=10000, help="Temporary in-memory HP for both actors.")
    parser.add_argument("--redis-url", default=settings.effective_redis_url)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.iterations <= 0:
        parser.error("--iterations must be positive")

    report = asyncio.run(
        probe_session(
            session_id=args.session_id,
            source_id=args.source,
            target_id=args.target,
            iterations=args.iterations,
            hp=args.hp,
            redis_url=args.redis_url,
        )
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_text_report(report)
    return 0


async def probe_session(
    *,
    session_id: str,
    source_id: str,
    target_id: str,
    iterations: int,
    hp: int,
    redis_url: str,
) -> dict[str, Any]:
    client = redis.Redis.from_url(redis_url, decode_responses=True)
    try:
        data_service = CombatSessionIntegration.from_redis(RedisAdapter(client))  # type: ignore[arg-type]
        battle_ctx = await data_service.load_battle_context(session_id)
    finally:
        await client.aclose()

    if battle_ctx is None:
        raise SystemExit(f"Combat session not found: {session_id}")

    source = battle_ctx.get_actor(int(source_id) if source_id.lstrip("-").isdigit() else source_id)
    target = battle_ctx.get_actor(int(target_id) if target_id.lstrip("-").isdigit() else target_id)
    if source is None or target is None:
        raise SystemExit(f"Actors not found in session {session_id}: source={source_id} target={target_id}")

    source_template = _prepare_actor(source, hp)
    target_template = _prepare_actor(target, hp)
    move = CombatMoveDTO(
        move_id="probe",
        char_id=source_template.meta.id,
        strategy="exchange",
        payload=ExchangePayload(target_id=target_template.meta.id),
    )

    expected = _expected_main_hand(source_template, target_template, move)
    stats = ProbeStats()
    pipeline = CombatExecutor().pipeline
    for _ in range(iterations):
        probe_source = copy.deepcopy(source_template)
        probe_target = copy.deepcopy(target_template)
        result = await pipeline.calculate(
            source=probe_source,
            target=probe_target,
            move=move,
            external_mods={"action_mode": "exchange"},
            exchange_count=probe_source.meta.exchange_counter,
        )
        stats.record(result)

    return {
        "session_id": session_id,
        "source": _actor_report(source_template),
        "target": _actor_report(target_template),
        "expected_main_hand": expected,
        "observed": stats.summary(),
    }


def _prepare_actor(actor: ActorSnapshot, hp: int) -> ActorSnapshot:
    result = copy.deepcopy(actor)
    result.meta.hp = hp
    result.meta.max_hp = hp
    result.meta.is_dead = False
    StatsEngine.ensure_stats(result)
    return result


def _expected_main_hand(source: ActorSnapshot, target: ActorSnapshot, move: CombatMoveDTO) -> dict[str, Any]:
    ctx = ContextBuilder.build_context(source, target, move, {"action_mode": "exchange"})
    source_stats = _stats(source)
    target_stats = _stats(target)
    weapon_class = ctx.flags.meta.weapon_class
    weapon_skill = float(getattr(source_stats.skills, f"skill_{weapon_class}", 0.0)) if weapon_class else 0.0
    accuracy = (source_stats.mods.main_hand_accuracy + source_stats.mods.accuracy) * ctx.mods.accuracy_mult
    crit_base = source_stats.mods.main_hand_crit_chance + source_stats.mods.crit_chance
    crit = min(crit_base * (1.0 + weapon_skill), source_stats.mods.main_hand_crit_cap)
    evasion = min(target_stats.mods.evasion - source_stats.mods.anti_dodge_chance, target_stats.mods.dodge_cap)
    parry = min(
        target_stats.mods.parry * (1.0 + 4.0 * target_stats.skills.skill_parrying),
        target_stats.mods.parry_cap,
    )
    block = min(
        target_stats.mods.block * (1.0 + 1.5 * target_stats.skills.skill_parrying),
        target_stats.mods.shield_block_cap,
    )
    return {
        "accuracy": round(accuracy, 6),
        "crit_after_hit": round(crit, 6),
        "evasion_after_hit": round(evasion, 6),
        "parry_after_not_dodged": round(parry, 6),
        "block_after_not_parried": round(block, 6),
        "weapon_class": weapon_class,
        "source_type": ctx.flags.meta.source_type,
    }


def _stats(actor: ActorSnapshot) -> ActorStats:
    if actor.stats is None:
        raise RuntimeError(f"Actor {actor.meta.id} has no stats after StatsEngine.ensure_stats")
    return actor.stats


def _actor_report(actor: ActorSnapshot) -> dict[str, Any]:
    stats = _stats(actor)
    return {
        "id": actor.meta.id,
        "name": actor.meta.name,
        "hp": actor.meta.hp,
        "layout": dict(actor.loadout.layout),
        "stats": {
            "main_hand_accuracy": stats.mods.main_hand_accuracy,
            "accuracy": stats.mods.accuracy,
            "main_hand_crit_chance": stats.mods.main_hand_crit_chance,
            "crit_chance": stats.mods.crit_chance,
            "main_hand_crit_cap": stats.mods.main_hand_crit_cap,
            "evasion": stats.mods.evasion,
            "anti_dodge_chance": stats.mods.anti_dodge_chance,
            "parry": stats.mods.parry,
            "block": stats.mods.block,
            "main_hand_damage_base": stats.mods.main_hand_damage_base,
            "physical_damage": stats.mods.physical_damage,
            "armor": stats.mods.armor,
            "physical_resistance": stats.mods.physical_resistance,
        },
    }


def print_text_report(report: dict[str, Any]) -> None:
    print(f"Session: {report['session_id']}")
    print(f"Source: {report['source']['name']} ({report['source']['id']})")
    print(f"Target: {report['target']['name']} ({report['target']['id']})")
    print()
    print("Expected main-hand chances:")
    for key, value in report["expected_main_hand"].items():
        print(f"  {key}: {value}")
    print()
    print("Observed:")
    observed = report["observed"]
    for key, value in observed.items():
        if key == "damage":
            print(f"  damage: count={value['count']} avg={value['avg']} min={value['min']} max={value['max']}")
        else:
            print(f"  {key}: {value}")


def _rate(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


if __name__ == "__main__":
    raise SystemExit(main())

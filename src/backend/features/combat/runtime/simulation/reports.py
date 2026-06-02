"""Human-readable reporting helpers for simulated combat runs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.features.combat.runtime.simulation.simulator import SimulationRunResult


def render_simulation_report(result: SimulationRunResult) -> str:
    """Render a compact report suitable for training logs."""
    telemetry = result.telemetry
    lines = [
        f"winner: {result.winner}",
        f"completion_reason: {result.completion_reason}",
        f"rounds: {result.rounds_completed}",
        f"actions: {telemetry.action_count}",
        f"failed_actions: {telemetry.failed_action_count}",
        f"damage_by_actor: {telemetry.damage_by_actor}",
        f"damage_taken_by_actor: {telemetry.damage_taken_by_actor}",
        f"armor_absorbed_by_actor: {telemetry.armor_absorbed_by_actor}",
        f"armor_absorb_events_by_actor: {telemetry.armor_absorb_events_by_actor}",
        f"healing_by_actor: {telemetry.healing_by_actor}",
        f"resource_spent_by_actor: {telemetry.resource_spent_by_actor}",
        f"action_count_by_actor: {telemetry.action_count_by_actor}",
        f"target_count_by_actor: {telemetry.target_count_by_actor}",
        f"targeted_by_actor: {telemetry.targeted_by_actor}",
        f"damage_events_by_actor: {telemetry.damage_events_by_actor}",
        f"incoming_events_by_actor: {telemetry.incoming_events_by_actor}",
        f"checks_by_actor: hit={telemetry.hit_by_actor} miss={telemetry.miss_by_actor} "
        f"dodge={telemetry.dodge_by_actor} parry={telemetry.parry_by_actor} "
        f"block={telemetry.block_by_actor} crit={telemetry.crit_by_actor}",
        f"overkill_by_actor: {telemetry.overkill_by_actor}",
        f"tactical_trigger_attempts_by_id: {telemetry.tactical_trigger_attempts_by_id}",
        f"tactical_trigger_success_by_id: {telemetry.tactical_trigger_success_by_id}",
        f"tactical_damage_by_actor: {telemetry.tactical_damage_by_actor}",
        f"tactical_reflected_by_actor: {telemetry.tactical_reflected_by_actor}",
        f"tactical_prevented_by_actor: {telemetry.tactical_prevented_by_actor}",
        f"tactical_chain_hits_by_actor: {telemetry.tactical_chain_hits_by_actor}",
        f"tactical_shield_branch_by_actor: {telemetry.tactical_shield_branch_by_actor}",
        f"tactical_shield_damage_by_actor: {telemetry.tactical_shield_damage_by_actor}",
        f"tactical_shield_absorbed_by_actor: {telemetry.tactical_shield_absorbed_by_actor}",
        f"tactical_shield_reflected_by_actor: {telemetry.tactical_shield_reflected_by_actor}",
        f"ranged_position_outgoing_by_actor: {telemetry.ranged_position_outgoing_by_actor}",
        f"ranged_position_incoming_by_actor: {telemetry.ranged_position_incoming_by_actor}",
        f"ranged_position_defense_attempts_by_actor: {telemetry.ranged_position_defense_attempts_by_actor}",
        f"ranged_position_defense_success_by_actor: {telemetry.ranged_position_defense_success_by_actor}",
        f"ranged_position_outgoing_damage_by_actor: {telemetry.ranged_position_outgoing_damage_by_actor}",
        f"ranged_position_incoming_damage_by_actor: {telemetry.ranged_position_incoming_damage_by_actor}",
        f"deaths: {telemetry.deaths}",
        f"feints: {telemetry.feint_pick_count}",
    ]
    if telemetry.round_events:
        lines.append("round_events:")
        for event in telemetry.round_events:
            lines.append(
                "  "
                f"round={event.get('round')} "
                f"{event.get('source_id')} -> {event.get('target_id')} "
                f"damage={event.get('damage')} healing={event.get('healing')} "
                f"skip={event.get('skip_reason') or '-'} deaths={event.get('deaths') or []}"
            )
    return "\n".join(lines)

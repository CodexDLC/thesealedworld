"""Diagnostic trace helpers — write to InteractionResultDTO and emit loguru events."""

from __future__ import annotations

from typing import Any

from loguru import logger as log

from src.backend.features.combat.dto.pipeline import (
    CombatCheckTraceDTO,
    CombatDamageTraceDTO,
    InteractionResultDTO,
)


def compact_details(details: dict[str, Any]) -> str:
    parts = []
    for key, value in details.items():
        if value is None:
            continue
        if isinstance(value, float):
            parts.append(f"{key}={value:.3f}")
        else:
            parts.append(f"{key}={value}")
    return " ".join(parts)


def compact_trace_details(details: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in details.items() if value is not None}


def trace_roll(
    res: InteractionResultDTO,
    stage: str,
    chance: float,
    roll: float | None,
    passed: bool,
    **details: Any,
) -> None:
    compacted = compact_trace_details(details)
    res.checks.append(
        CombatCheckTraceDTO(
            stage=stage,
            chance=chance,
            roll=roll,
            passed=passed,
            details=compacted,
        )
    )
    log.bind(
        source_id=res.source_id,
        target_id=res.target_id,
        stage=stage,
        chance=chance,
        roll="auto" if roll is None else round(roll, 3),
        passed=passed,
        details=compacted,
    ).debug("CombatRoll")


def trace_step(res: InteractionResultDTO, stage: str, outcome: str, **details: Any) -> None:
    log.bind(
        source_id=res.source_id,
        target_id=res.target_id,
        stage=stage,
        outcome=outcome,
        details=details,
    ).debug("CombatStep")


def trace_damage(res: InteractionResultDTO, **details: Any) -> None:
    final = details.pop("final")
    raw = details.pop("raw")
    min_d = details.pop("min_d")
    max_d = details.pop("max_d")
    compacted = compact_trace_details(details)
    res.damage_trace = CombatDamageTraceDTO(
        raw=float(raw),
        final=float(final),
        min=float(min_d),
        max=float(max_d),
        details=compacted,
    )
    log.bind(
        source_id=res.source_id,
        target_id=res.target_id,
        final=round(float(final), 2),
        raw=round(float(raw), 2),
        min_damage=round(float(min_d), 2),
        max_damage=round(float(max_d), 2),
        details=compacted,
    ).debug("CombatDamage")

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from loguru import logger as log

from src.backend.features.items.resources.modifier_contracts.catalog import get_modifier_contract
from src.backend.features.items.resources.modifier_contracts.compiler import compile_modifier_command

if TYPE_CHECKING:
    from src.backend.features.combat.dto import ActorSnapshot
    from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
    from src.backend.features.items.resources.modifier_contracts.schemas import ModifierContractDTO

ModifierApplicationOwner = Literal["ability", "feint", "effect"]


@dataclass
class AppliedModifierSources:
    modified_keys: set[str] = field(default_factory=set)
    modified_sources: dict[str, list[str]] = field(default_factory=dict)


class ModifierApplicationService:
    """Compiles combat modifier applications into raw.temp waterfall commands."""

    @staticmethod
    def apply(
        *,
        applications: list[ModifierApplicationDTO],
        owner: ModifierApplicationOwner,
        owner_uid: str,
        owner_id: str,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
    ) -> AppliedModifierSources:
        applied = AppliedModifierSources()
        for application in applications:
            target_actor = ModifierApplicationService._resolve_target_actor(application, source, target, owner)
            if target_actor is None:
                continue

            contract = get_modifier_contract(application.modifier_id)
            if contract is None:
                log.bind(modifier_id=application.modifier_id).warning("ModifierApplicationUnknownContract")
                continue

            value = ModifierApplicationService._resolve_value(application)
            source_id = ModifierApplicationService.source_id(owner, owner_uid, owner_id, application.modifier_id)
            stat_key = ModifierApplicationService._write_temp_command(target_actor, contract, value, source_id)

            applied.modified_keys.add(stat_key)
            applied.modified_sources.setdefault(stat_key, []).append(source_id)

        return applied

    @staticmethod
    def source_id(owner: ModifierApplicationOwner, owner_uid: str, owner_id: str, modifier_id: str) -> str:
        return f"{owner}:{owner_uid}:{owner_id}:{modifier_id}"

    @staticmethod
    def remove_temp_sources(actor: ActorSnapshot, modified_sources: dict[str, list[str]]) -> None:
        for stat_key, source_ids in modified_sources.items():
            for layer in (actor.raw.attributes, actor.raw.modifiers):
                stat_data = layer.get(stat_key)
                if not isinstance(stat_data, dict):
                    continue

                temp_data = stat_data.get("temp")
                if not isinstance(temp_data, dict):
                    continue

                removed = False
                for source_id in source_ids:
                    if source_id in temp_data:
                        del temp_data[source_id]
                        removed = True

                if removed:
                    actor.dirty_stats.add(stat_key)

    @staticmethod
    def _resolve_target_actor(
        application: ModifierApplicationDTO,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        owner: ModifierApplicationOwner,
    ) -> ActorSnapshot | None:
        target_actor = application.target_actor
        if owner == "effect":
            if target_actor in {"self", "target", "defender"}:
                return target
            if target_actor == "attacker":
                return source
        if target_actor in {"self", "attacker"}:
            return source
        if target_actor in {"target", "defender"}:
            return target
        return None

    @staticmethod
    def _resolve_value(application: ModifierApplicationDTO) -> float:
        if application.value_mode == "base":
            if application.value_override is not None:
                return application.value_override
            return application.value_multiplier

        if application.value_mode == "base_multiplier":
            base = application.value_override if application.value_override is not None else 1.0
            return base * application.value_multiplier

        if application.value_mode == "override":
            if application.value_override is not None:
                return application.value_override
            return application.value_multiplier

        raise ValueError(f"Unsupported modifier application value mode: {application.value_mode!r}")

    @staticmethod
    def _write_temp_command(
        actor: ActorSnapshot,
        contract: ModifierContractDTO,
        value: float,
        source_id: str,
    ) -> str:
        stat_key = contract.target_field
        target_layer = ModifierApplicationService._target_layer(actor, contract)
        stat_data = target_layer.get(stat_key)
        if not isinstance(stat_data, dict):
            default_base = 1.0 if contract.operation == "mult" else 0.0
            stat_data = {"base": stat_data if stat_data is not None else default_base, "source": {}, "temp": {}}
            target_layer[stat_key] = stat_data

        stat_data.setdefault("source", {})
        if contract.operation == "mult" and "base" not in stat_data:
            stat_data["base"] = 1.0
        temp_data = stat_data.setdefault("temp", {})
        temp_data[source_id] = compile_modifier_command(contract, value)
        actor.dirty_stats.add(stat_key)
        return stat_key

    @staticmethod
    def _target_layer(actor: ActorSnapshot, contract: ModifierContractDTO) -> dict:
        if contract.default_layer == "attributes":
            return actor.raw.attributes
        if contract.default_layer == "modifiers":
            return actor.raw.modifiers
        if contract.default_layer == "auto" and contract.target_field in actor.raw.attributes:
            return actor.raw.attributes
        return actor.raw.modifiers

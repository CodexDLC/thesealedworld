from __future__ import annotations

from typing import Any

from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import (
    PipelineMutationApplicationDTO,
    PipelineMutationContractDTO,
    PipelineMutationSource,
    get_pipeline_mutation_contract,
)


class PipelineMutationService:
    """Applies whitelisted pipeline-local mutations to one exchange context/result."""

    @staticmethod
    def apply(
        *,
        applications: list[PipelineMutationApplicationDTO],
        ctx: Any,
        source: PipelineMutationSource,
    ) -> None:
        for application in applications:
            contract = get_pipeline_mutation_contract(application.mutation_id)
            if contract is None:
                raise ValueError(f"Unknown pipeline mutation id: {application.mutation_id!r}")
            if source not in contract.allowed_sources:
                raise ValueError(f"Source {source!r} cannot apply pipeline mutation {application.mutation_id!r}")

            raw_value = application.value_override if application.value_override is not None else contract.default_value
            value = PipelineMutationService._coerce_value(contract, raw_value)
            PipelineMutationService._set_path(ctx, contract.path, value)

    @staticmethod
    def _set_path(ctx: Any, path: str, value: Any) -> None:
        parts = path.split(".")
        obj = ctx
        for part in parts[:-1]:
            if not hasattr(obj, part):
                raise ValueError(f"Invalid pipeline mutation path: {path!r}")
            obj = getattr(obj, part)
        field_name = parts[-1]
        if not hasattr(obj, field_name):
            raise ValueError(f"Invalid pipeline mutation path: {path!r}")
        setattr(obj, field_name, value)

    @staticmethod
    def _coerce_value(contract: PipelineMutationContractDTO, value: Any) -> Any:
        if contract.value_kind == "bool":
            if not isinstance(value, bool):
                raise ValueError(f"Pipeline mutation {contract.id!r} expects bool, got {type(value).__name__}")
            return value
        if contract.value_kind == "int":
            if isinstance(value, bool):
                raise ValueError(f"Pipeline mutation {contract.id!r} expects int, got bool")
            return int(value)
        if contract.value_kind == "float":
            if isinstance(value, bool):
                raise ValueError(f"Pipeline mutation {contract.id!r} expects float, got bool")
            return float(value)
        if contract.value_kind == "str":
            if value is None:
                return None
            return str(value)
        if contract.value_kind == "tuple_float":
            if value is None:
                return None
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ValueError(f"Pipeline mutation {contract.id!r} expects two numeric values")
            return (float(value[0]), float(value[1]))
        raise ValueError(f"Unsupported pipeline mutation kind: {contract.value_kind!r}")

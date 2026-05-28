from __future__ import annotations

import random
from typing import Any


class ZoneAssemblyPlanner:
    """Selects scale and zone assembly presets for a rift run."""

    def select_plan(
        self,
        *,
        setting: dict[str, Any],
        scale_presets: dict[str, dict[str, Any]],
        assembly_presets: dict[str, dict[str, Any]],
        seed: str | None = None,
        requested_scale_key: str | None = None,
        requested_assembly_preset_key: str | None = None,
        use_default_scale: bool = True,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        options = dict(setting.get("assembly_options") or {})
        resolved_seed = seed or str(options.get("default_seed") or "rift-dev")
        allowed_scale_keys = _allowed_keys(options.get("allowed_scale_preset_keys"), scale_presets)
        allowed_assembly_keys = _allowed_keys(options.get("allowed_zone_assembly_preset_keys"), assembly_presets)
        rng = random.Random(f"{resolved_seed}:zone-assembly-plan")

        scale_key = requested_scale_key or (
            str(options.get("default_scale_preset_key") or "") if use_default_scale else ""
        )
        if not scale_key:
            scale_key = rng.choice(allowed_scale_keys)
        if scale_key not in allowed_scale_keys:
            raise ValueError(f"Rift scale preset is not allowed: {scale_key}")

        scale_preset = scale_presets[scale_key]
        assembly_key = requested_assembly_preset_key
        if assembly_key is None:
            scale_assembly_keys = [
                key
                for key in scale_preset.get("zone_assembly_preset_keys", [])
                if isinstance(key, str) and key in allowed_assembly_keys
            ]
            candidates = scale_assembly_keys or allowed_assembly_keys
            assembly_key = rng.choice(candidates)
        if assembly_key not in allowed_assembly_keys:
            raise ValueError(f"Rift zone assembly preset is not allowed: {assembly_key}")

        return scale_preset, assembly_presets[assembly_key]


def select_zone_assembly_plan(
    *,
    setting: dict[str, Any],
    scale_presets: dict[str, dict[str, Any]],
    assembly_presets: dict[str, dict[str, Any]],
    seed: str | None = None,
    requested_scale_key: str | None = None,
    requested_assembly_preset_key: str | None = None,
    use_default_scale: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return ZoneAssemblyPlanner().select_plan(
        setting=setting,
        scale_presets=scale_presets,
        assembly_presets=assembly_presets,
        seed=seed,
        requested_scale_key=requested_scale_key,
        requested_assembly_preset_key=requested_assembly_preset_key,
        use_default_scale=use_default_scale,
    )


def _allowed_keys(raw_keys: Any, presets: dict[str, dict[str, Any]]) -> list[str]:
    if not isinstance(raw_keys, list):
        return sorted(presets)
    result = [key for key in raw_keys if isinstance(key, str) and key in presets]
    if not result:
        raise ValueError("Rift preset allow-list does not contain usable keys")
    return result

"""Policy artifact loader with safe default fallback and archetype merge."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from loguru import logger as log
from pydantic import ValidationError

from src.backend.features.combat.runtime.ai.archetypes import (
    Archetype,
    archetype_policy_filename,
)
from src.backend.features.combat.runtime.ai.policy import Policy

_POLICIES_DIR = Path(__file__).resolve().parent / "policies"
_DEFAULT_POLICY_PATH = _POLICIES_DIR / "default_policy.json"
_ENV_VAR = "COMBAT_AI_POLICY_PATH"


class PolicyStore:
    """Load and cache combat AI policies.

    Resolution order (no ``archetype`` argument):

    1. Explicit ``path`` argument to :meth:`load`.
    2. ``COMBAT_AI_POLICY_PATH`` environment variable (set process-wide).
    3. Bundled ``policies/default_policy.json``.

    With an ``archetype`` argument, the archetype JSON is merged *on top of*
    the resolved base policy (default + env-override). Missing weight keys
    are filled from the base, so archetype JSONs only need to list overrides.

    Loads are cached per ``(absolute_path, mtime_ns)``; archetype merges are
    cached per ``(base_key, archetype_id)``. A malformed external artifact
    triggers a safe fallback to the default policy and a warning log.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, int], Policy] = {}
        self._merged_cache: dict[tuple[tuple[str, int], str], Policy] = {}
        self._lock = Lock()

    def load(
        self,
        path: Path | str | None = None,
        *,
        archetype: str | None = None,
        policy_id: str | None = None,
    ) -> Policy:
        # Highest precedence: explicit policy_id from CombatAiConfig namespace.
        # Non-empty id resolves to policies/{policy_id}.json. Unknown ids fall
        # through to env/default via _load_base's normal fallback chain.
        resolved_path = path
        if resolved_path is None and policy_id:
            candidate = _POLICIES_DIR / f"{policy_id}.json"
            if candidate.exists():
                resolved_path = candidate
            else:
                log.bind(policy_id=policy_id, candidate=str(candidate)).warning("CombatAiPolicyIdUnknown")
        base, base_key = self._load_base(resolved_path)
        if archetype is None:
            return base
        return self._apply_archetype(base, base_key, Archetype.coerce(archetype))

    def _load_base(self, path: Path | str | None) -> tuple[Policy, tuple[str, int] | None]:
        candidate = self._resolve_path(path)
        try:
            policy = self._load_validated(candidate)
            if policy is not None:
                return policy, self._cache_key(candidate)
        except (OSError, ValidationError, ValueError) as exc:
            log.bind(policy_path=str(candidate), reason=str(exc)).warning("CombatAiPolicyLoadFailed")

        if candidate != _DEFAULT_POLICY_PATH:
            try:
                default = self._load_validated(_DEFAULT_POLICY_PATH)
                if default is not None:
                    return default, self._cache_key(_DEFAULT_POLICY_PATH)
            except (OSError, ValidationError, ValueError) as exc:
                log.bind(policy_path=str(_DEFAULT_POLICY_PATH), reason=str(exc)).error(
                    "CombatAiDefaultPolicyLoadFailed"
                )

        return Policy.with_defaults(), None

    def _apply_archetype(
        self,
        base: Policy,
        base_key: tuple[str, int] | None,
        archetype: Archetype,
    ) -> Policy:
        if archetype is Archetype.BALANCED:
            return base

        archetype_path = _POLICIES_DIR / archetype_policy_filename(archetype)
        merge_key = (base_key or ("__virtual__", 0), archetype.value)
        with self._lock:
            cached = self._merged_cache.get(merge_key)
            if cached is not None:
                return cached

        try:
            overlay = self._load_validated(archetype_path)
        except (OSError, ValidationError, ValueError) as exc:
            log.bind(archetype=archetype.value, path=str(archetype_path), reason=str(exc)).warning(
                "CombatAiArchetypePolicyLoadFailed"
            )
            overlay = None

        if overlay is None:
            return base

        merged_weights = dict(base.weights)
        merged_weights.update(overlay.weights)
        merged_metadata = dict(base.metadata)
        merged_metadata.update(overlay.metadata)
        merged_metadata["archetype"] = archetype.value
        merged = Policy(
            policy_id=overlay.policy_id or f"{base.policy_id}+{archetype.value}",
            version=overlay.version,
            weights=merged_weights,
            metadata=merged_metadata,
        )
        with self._lock:
            self._merged_cache[merge_key] = merged
        return merged

    @staticmethod
    def _resolve_path(path: Path | str | None) -> Path:
        import os

        if path is not None:
            return Path(path)
        env = os.environ.get(_ENV_VAR)
        if env:
            return Path(env)
        return _DEFAULT_POLICY_PATH

    @staticmethod
    def _cache_key(path: Path) -> tuple[str, int] | None:
        try:
            return (str(path.resolve()), path.stat().st_mtime_ns)
        except OSError:
            return None

    def _load_validated(self, path: Path) -> Policy | None:
        if not path.exists():
            return None
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            return None
        key = (str(path.resolve()), mtime_ns)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached
        policy = Policy.from_path(path)
        with self._lock:
            self._cache[key] = policy
        return policy

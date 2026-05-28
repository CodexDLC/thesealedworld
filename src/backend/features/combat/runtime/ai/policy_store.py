"""Policy artifact loader with safe default fallback."""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from loguru import logger as log
from pydantic import ValidationError

from src.backend.features.combat.runtime.ai.policy import Policy

_DEFAULT_POLICY_PATH = Path(__file__).resolve().parent / "policies" / "default_policy.json"
_ENV_VAR = "COMBAT_AI_POLICY_PATH"


class PolicyStore:
    """Load and cache combat AI policies.

    Resolution order:

    1. Explicit ``path`` argument to :meth:`load`.
    2. ``COMBAT_AI_POLICY_PATH`` environment variable (set process-wide).
    3. Bundled ``policies/default_policy.json`` shipped with the source.

    Loads are cached by ``(absolute_path, mtime_ns)``; the cache is shared
    across calls on the same process so the combat worker does not re-parse
    JSON on every AI decision. A malformed external artifact triggers a
    safe fallback to the default policy and a warning log.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, int], Policy] = {}
        self._lock = Lock()

    def load(self, path: Path | str | None = None) -> Policy:
        candidate = self._resolve_path(path)
        try:
            policy = self._load_validated(candidate)
            if policy is not None:
                return policy
        except (OSError, ValidationError, ValueError) as exc:
            log.bind(policy_path=str(candidate), reason=str(exc)).warning("CombatAiPolicyLoadFailed")

        if candidate != _DEFAULT_POLICY_PATH:
            try:
                default = self._load_validated(_DEFAULT_POLICY_PATH)
                if default is not None:
                    return default
            except (OSError, ValidationError, ValueError) as exc:
                log.bind(policy_path=str(_DEFAULT_POLICY_PATH), reason=str(exc)).error(
                    "CombatAiDefaultPolicyLoadFailed"
                )

        return Policy.with_defaults()

    @staticmethod
    def _resolve_path(path: Path | str | None) -> Path:
        if path is not None:
            return Path(path)
        env = os.environ.get(_ENV_VAR)
        if env:
            return Path(env)
        return _DEFAULT_POLICY_PATH

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

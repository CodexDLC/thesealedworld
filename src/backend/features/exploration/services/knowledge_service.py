from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.exploration.services.knowledge_runtime import ExplorationKnowledgeRuntimeManager

DEFAULT_LOCATION_XP_CAPS: dict[str, float] = {
    "movement": 10.0,
    "scouting": 10.0,
    "hunting": 10.0,
}

SKILL_TO_BUDGET: dict[str, str] = {
    "skill_pathfinder": "movement",
    "skill_scouting": "scouting",
    "skill_hunting": "hunting",
}


class ExplorationKnowledgeService:
    def __init__(
        self,
        runtime: ExplorationKnowledgeRuntimeManager,
        *,
        default_caps: dict[str, float] | None = None,
    ) -> None:
        self.runtime = runtime
        self.default_caps = dict(default_caps or DEFAULT_LOCATION_XP_CAPS)

    async def cap_rewards(self, char_id: int, loc_id: str, rewards: dict[str, float]) -> dict[str, float]:
        if not rewards:
            return {}

        document = await self.runtime.get(char_id, loc_id)
        knowledge = self._normalize_document(char_id, loc_id, document)
        capped: dict[str, float] = {}

        for skill_key, raw_delta in rewards.items():
            budget_key = SKILL_TO_BUDGET.get(skill_key)
            if budget_key is None:
                capped[skill_key] = float(raw_delta)
                continue

            spent_key = f"{budget_key}_xp_spent"
            cap_key = f"{budget_key}_xp_cap"
            spent = _number(knowledge.get(spent_key))
            cap = _number(knowledge.get(cap_key))
            if spent >= cap:
                continue
            capped[skill_key] = round(float(raw_delta), 4)
            knowledge[spent_key] = round(spent + 1.0, 4)

        knowledge["last_visited_at"] = datetime.now(UTC).isoformat()
        knowledge["knowledge_status"] = self.status(knowledge)
        await self.runtime.set(char_id, loc_id, knowledge, mark_dirty=True)
        return capped

    def status(self, document: dict[str, Any]) -> str:
        movement_spent = _number(document.get("movement_xp_spent"))
        scouting_spent = _number(document.get("scouting_xp_spent"))
        movement_cap = _number(document.get("movement_xp_cap"))
        scouting_cap = _number(document.get("scouting_xp_cap"))
        if movement_cap > 0 and scouting_cap > 0 and movement_spent >= movement_cap and scouting_spent >= scouting_cap:
            return "fully_studied"
        if any(
            _number(document.get(key)) > 0 for key in ("movement_xp_spent", "scouting_xp_spent", "hunting_xp_spent")
        ):
            return "partially_studied"
        return "visited"

    def _normalize_document(self, char_id: int, loc_id: str, document: dict[str, Any] | None) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        knowledge = dict(document or {})
        knowledge["character_id"] = int(char_id)
        knowledge["loc_id"] = str(loc_id)
        for budget_key, cap in self.default_caps.items():
            knowledge.setdefault(f"{budget_key}_xp_spent", 0.0)
            knowledge.setdefault(f"{budget_key}_xp_cap", float(cap))
        knowledge.setdefault("discovered_at", now)
        knowledge.setdefault("last_visited_at", now)
        knowledge.setdefault("metadata", {})
        knowledge.setdefault("context", {})
        knowledge.setdefault("source_context", {})
        knowledge.setdefault("schema_version", 1)
        knowledge.setdefault("revision", 0)
        return knowledge


def _number(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0

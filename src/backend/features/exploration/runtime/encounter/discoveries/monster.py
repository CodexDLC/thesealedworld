from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from src.backend.infrastructure.actor_commitments import ActorCommitmentManager
from src.shared.schemas.exploration import (
    DetectionStatus,
    EncounterDTO,
    EncounterOptionDTO,
    EncounterType,
    EnemyPreviewDTO,
)

if TYPE_CHECKING:
    from src.backend.features.exploration.integrations.encounter_integration import EncounterIntegration
    from src.backend.features.monsters.dto import MonsterGroupMemberPreview, MonsterGroupResult


class MonsterDiscoveryBuilder:
    """Builds reusable monster discovery payloads for travel and scouting modes."""

    async def build(
        self,
        *,
        char_id: int,
        loc_id: str,
        tier: int,
        difficulty: str,
        status: DetectionStatus,
        budget: float,
        hunting_skill: float = 0.0,
        integration: EncounterIntegration,
    ) -> EncounterDTO:
        encounter_id = f"monster-{uuid.uuid4().hex[:12]}"
        group = await integration.prepare_monster_group(
            loc_id,
            budget,
            force_single_family=True,
            scope_id=encounter_id,
            correlation_id=encounter_id,
        )
        combat_request = self._combat_request(
            char_id=char_id,
            loc_id=loc_id,
            encounter_id=encounter_id,
            group=group,
        )
        combat = await self._request_combat(integration, combat_request, encounter_id)
        intel_level = hunting_intel_level(hunting_skill)
        enemies = [self._enemy_preview(preview, intel_level=intel_level) for preview in group.previews]
        description = self._description(status, group)
        options = self._options(status)
        return EncounterDTO(
            id=encounter_id,
            type=EncounterType.COMBAT,
            status=status,
            title="ЗАСАДА!" if status == DetectionStatus.AMBUSH else "УГРОЗА ОБНАРУЖЕНА",
            description=description,
            enemies=enemies,
            info_level=intel_level,
            options=options,
            session_id=str(combat.get("combat_id") or combat_request["combat_id"]),
            metadata={
                "kind": "monster_group",
                "loc_id": loc_id,
                "tier": tier,
                "difficulty": difficulty,
                "budget": budget,
                "intel": {
                    "skill_key": "skill_hunting",
                    "level": intel_level,
                    "value": _normalized_skill(hunting_skill),
                },
                "monster_group": group.model_dump(mode="json"),
                "combat": {
                    "status": combat.get("status") or "requested",
                    "combat_id": combat.get("combat_id") or combat_request["combat_id"],
                    "request": combat_request,
                    "response": combat,
                },
            },
        )

    def _combat_request(
        self,
        *,
        char_id: int,
        loc_id: str,
        encounter_id: str,
        group: MonsterGroupResult,
    ) -> dict[str, Any]:
        combat_id = f"combat-{encounter_id}"
        return {
            "combat_id": combat_id,
            "source": "exploration",
            "battle_type": "pve",
            "requested_by": char_id,
            "participants": {"team_1": [char_id], "team_2": list(group.monster_ids)},
            "commitments": self._monster_commitments(group),
            "location_id": loc_id,
            "ttl": 3600,
            "metadata": {
                "encounter_id": encounter_id,
                "monster_group_id": group.group_id,
                "clan_id": group.clan_id,
                "family_id": group.family_id,
            },
        }

    @staticmethod
    async def _request_combat(
        integration: EncounterIntegration,
        combat_request: dict[str, Any],
        encounter_id: str,
    ) -> dict[str, Any]:
        try:
            return await integration.request_combat_session(combat_request, correlation_id=encounter_id)
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "failed",
                "combat_id": combat_request.get("combat_id"),
                "error": f"{exc.__class__.__name__}: {exc}",
            }

    @staticmethod
    def _monster_commitments(group: MonsterGroupResult) -> dict[str, str]:
        commitments: dict[str, str] = {}
        for monster_id in group.monster_ids:
            source_ref = ActorCommitmentManager.source_ref("monster", monster_id)
            commitment = group.actor_commitments.get(source_ref)
            if commitment:
                commitments[source_ref] = str(commitment)
        return commitments

    @staticmethod
    def _enemy_preview(preview: MonsterGroupMemberPreview, *, intel_level: int) -> EnemyPreviewDTO:
        hp = preview.hp or {}
        hp_current = _int_or_none(hp.get("current") or hp.get("hp") or hp.get("hp_current"))
        hp_max = _int_or_none(hp.get("max") or hp.get("max_hp") or hp.get("hp_max"))
        hp_percent = None
        if hp_current is not None and hp_max:
            hp_percent = max(0, min(100, round(hp_current / hp_max * 100)))
        show_identity = intel_level >= 1
        show_combat_estimate = intel_level >= 2
        show_details = intel_level >= 3
        return EnemyPreviewDTO(
            name=preview.name if show_identity else "???",
            level=preview.member_tier if show_identity else None,
            member_tier=preview.member_tier if show_identity else None,
            hp_percent=hp_percent if show_combat_estimate else None,
            image=preview.image,
            visual=preview.visual,
            monster_id=preview.monster_id if show_identity else None,
            description=preview.description if show_combat_estimate else "???",
            role=preview.role if show_identity else "???",
            variant_key=preview.variant_key if show_identity else "???",
            threat_rating=preview.threat_rating if show_combat_estimate else None,
            hp=preview.hp if show_details else {},
            tags=preview.tags if show_details else [],
            intel_level=intel_level,
        )

    @staticmethod
    def _description(status: DetectionStatus, group: MonsterGroupResult) -> str:
        for preview in group.previews:
            text = preview.ambush_ru if status == DetectionStatus.AMBUSH else preview.detected_ru
            if text:
                return text
        for preview in group.previews:
            if preview.idle_ru:
                return preview.idle_ru
        for preview in group.previews:
            if preview.description:
                return preview.description

        if status == DetectionStatus.AMBUSH:
            return "Угроза выходит из укрытия раньше, чем вы успеваете оценить обстановку."
        return "Вы замечаете движение впереди и успеваете выбрать, как подойти к угрозе."

    @staticmethod
    def _options(status: DetectionStatus) -> list[EncounterOptionDTO]:
        if status == DetectionStatus.AMBUSH:
            return [
                EncounterOptionDTO(id="attack", label="В бой!", style="danger"),
                EncounterOptionDTO(id="bypass", label="Обойти", style="secondary"),
            ]
        return [
            EncounterOptionDTO(id="attack", label="Атаковать", style="danger"),
            EncounterOptionDTO(id="bypass", label="Обойти", style="secondary"),
            EncounterOptionDTO(id="inspect", label="Изучить", style="primary"),
        ]


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def hunting_intel_level(hunting_skill: Any) -> int:
    value = _normalized_skill(hunting_skill)
    if value >= 0.8:
        return 4
    if value >= 0.6:
        return 3
    if value >= 0.4:
        return 2
    if value >= 0.2:
        return 1
    return 0


def _normalized_skill(value: Any) -> float:
    try:
        raw = max(0.0, float(value or 0.0))
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, raw / 100.0 if raw > 1.0 else raw)

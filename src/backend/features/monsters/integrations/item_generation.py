from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.items.dto.instance import (
    ItemGenerationRequestDTO,
    ItemOriginRefDTO,
    RuntimeItemProjectionDTO,
)
from src.backend.features.monsters.dto.generation import (
    MonsterItemAffixPolicyDTO,
    MonsterItemBuildRequestDTO,
    MonsterItemsProjectionDTO,
)
from src.backend.features.monsters.resources.equipment_mapping import (
    MonsterNaturalEquipmentMapping,
    get_natural_equipment_mapping,
)
from src.backend.features.monsters.resources.item_affix_profiles import (
    get_monster_affix_count,
    get_monster_affix_step_count,
    get_monster_allowed_affixes,
    get_monster_boss_forced_affixes,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


def build_monster_item_request(
    *,
    owner_key: str,
    family_id: str,
    member_role: str,
    member_tier: int,
    slot: str,
    natural_key: str | None = None,
    base_id: str | None = None,
    item_kind: str | None = None,
    material_id: str | None = None,
    item_grade: str = "artifact",
    rarity_tier: int | None = None,
    seed: str | None = None,
    source_context: dict[str, object] | None = None,
) -> MonsterItemBuildRequestDTO:
    mapping = get_natural_equipment_mapping(natural_key) if natural_key else None
    resolved_kind = str(item_kind or (mapping.item_kind if mapping else "weapon"))
    resolved_slot = slot or (mapping.default_slot if mapping else "")
    allowed_affixes = get_monster_allowed_affixes(family_id, resolved_kind, resolved_slot)  # type: ignore[arg-type]
    forced_affixes = get_monster_boss_forced_affixes(family_id, resolved_slot) if member_role == "boss" else ()
    policy = MonsterItemAffixPolicyDTO(
        allowed_affix_ids=list(allowed_affixes),
        forced_affix_ids=[affix_id for affix_id in forced_affixes if affix_id in allowed_affixes],
        affix_count=get_monster_affix_count(member_role),
        affix_step_count=get_monster_affix_step_count(member_tier),
    )
    return MonsterItemBuildRequestDTO(
        owner_key=owner_key,
        family_id=family_id,
        member_role=member_role,  # type: ignore[arg-type]
        member_tier=member_tier,
        slot=resolved_slot,
        mode="natural" if mapping else "base",
        item_kind=resolved_kind,  # type: ignore[arg-type]
        base_id=base_id,
        natural_key=natural_key,
        material_id=material_id,
        item_grade=item_grade,
        rarity_tier=member_tier if rarity_tier is None else rarity_tier,
        affix_policy=policy,
        seed=seed,
        source_context=source_context or {},
    )


def to_item_generation_request(request: MonsterItemBuildRequestDTO) -> ItemGenerationRequestDTO:
    mapping = (
        get_natural_equipment_mapping(request.natural_key)
        if request.mode == "natural" and request.natural_key
        else None
    )
    base_id = _resolve_base_id(request, mapping)
    material_id = request.material_id or (mapping.material_id if mapping else None)
    natural_tags = list(mapping.tags) if mapping else []
    runtime_metadata = {
        "owner_key": request.owner_key,
        "family_id": request.family_id,
        "member_role": request.member_role,
        "member_tier": request.member_tier,
    }
    if request.natural_key:
        runtime_metadata["natural_key"] = request.natural_key

    source_context = {
        "family_id": request.family_id,
        "member_role": request.member_role,
        "member_tier": request.member_tier,
        "item_kind": request.item_kind,
        **request.source_context,
    }
    return ItemGenerationRequestDTO(
        generation_mode="runtime",
        base_id=base_id,
        target_slot=request.slot,
        rarity_tier=request.rarity_tier,
        item_grade=request.item_grade or (mapping.item_grade if mapping else ""),
        material_id=material_id,
        forced_affix_ids=list(request.affix_policy.forced_affix_ids),
        allowed_affix_ids=list(request.affix_policy.allowed_affix_ids),
        affix_count=request.affix_policy.affix_count,
        affix_step_count=request.affix_policy.affix_step_count,
        extra_narrative_tags=natural_tags,
        runtime_metadata=runtime_metadata,
        source_context=source_context,
        source="monster_runtime_item",
        origin_ref=ItemOriginRefDTO(origin_type="system", origin_ref="monster_runtime_item", seed=request.seed),
        return_item=True,
    )


def to_item_generation_requests(requests: Iterable[MonsterItemBuildRequestDTO]) -> list[ItemGenerationRequestDTO]:
    return [to_item_generation_request(request) for request in requests]


def build_member_items_projection(
    items: Iterable[RuntimeItemProjectionDTO], owner_key: str
) -> MonsterItemsProjectionDTO:
    equipment: dict[str, str] = {}
    by_id: dict[str, dict[str, object]] = {}
    for item in items:
        if item.owner_key != owner_key:
            continue
        equipment[item.slot] = item.item_id
        by_id[item.item_id] = item.model_dump(mode="json")
    from src.backend.features.monsters.dto.generation import MonsterItemLayoutDTO

    layout = MonsterItemLayoutDTO(equipment=equipment, belt={})
    return MonsterItemsProjectionDTO(layout=layout, by_id=by_id)


def _resolve_base_id(request: MonsterItemBuildRequestDTO, mapping: MonsterNaturalEquipmentMapping | None) -> str:
    if mapping:
        return mapping.base_id
    if request.base_id:
        return request.base_id
    raise ValueError("Monster item request has no base_id")

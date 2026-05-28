from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any
from uuid import UUID

from loguru import logger

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.admin_players.dto import (
    AdminPlayerGenerateCharacterRequestDTO,
    AdminPlayerGenerateCharacterResponseDTO,
    AdminPlayerGenerationClanOptionDTO,
    AdminPlayerGenerationOptionsResponseDTO,
)
from src.backend.features.admin_players.services import _character_summary
from src.backend.features.items.dto.instance import ItemOriginRefDTO, ItemPlacementRefDTO
from src.backend.features.moderation import CharacterNamePolicy
from src.backend.features.monsters.integrations.item_generation import (
    build_monster_item_request,
    to_item_generation_request,
)
from src.backend.features.monsters.resources import get_available_variants_for_tier_window, get_family_config
from src.backend.features.monsters.resources.equipment_mapping import get_natural_equipment_mapping
from src.shared.enums import CoreDomain
from src.shared.enums.skill_enums import SkillProgressState
from src.shared.utils.character_name import CharacterNameError

if TYPE_CHECKING:
    from src.backend.features.monsters.resources.item_affix_profiles import MonsterItemAffixKind

_ATTRIBUTE_KEYS = (
    "strength",
    "agility",
    "endurance",
    "intellect",
    "memory",
    "mental",
    "perception",
    "projection",
    "prediction",
)

_FULL_LOADOUT: dict[str, str] = {
    "main_hand": "sword",
    "off_hand": "buckler",
    "head_armor": "hood",
    "chest_armor": "leather_armor",
    "arms_armor": "soft_bracers",
    "legs_armor": "scout_leggings",
    "chest_garment": "linen_shirt",
    "legs_garment": "fur_pants",
    "outer_garment": "winter_cloak",
    "gloves_garment": "work_gloves",
    "feetwear": "travel_boots",
    "amulet": "amulet",
    "earring": "earring",
    "ring_1": "ring",
    "ring_2": "ring",
    "belt_accessory": "belt",
}

_BASE_SKILLS = (
    "skill_swords",
    "skill_fencing",
    "skill_macing",
    "skill_ranged_combat",
    "skill_two_handed",
    "skill_dual_wield",
    "skill_shield_mastery",
    "skill_light_armor",
    "skill_medium_armor",
    "skill_tactics",
    "skill_archery",
    "skill_polearms",
)


class AdminPlayerCharacterGenerationService:
    MAX_SLOTS = 4
    INITIAL_LOCATION_ID = "52_52"

    def __init__(
        self,
        *,
        character_repo: Any,
        attributes_repo: Any,
        skill_repo: Any,
        progression_repo: Any,
        item_generation: Any,
        monster_repo: Any,
        name_policy: CharacterNamePolicy | None = None,
    ) -> None:
        self.character_repo = character_repo
        self.attributes_repo = attributes_repo
        self.skill_repo = skill_repo
        self.progression_repo = progression_repo
        self.item_generation = item_generation
        self.monster_repo = monster_repo
        self.name_policy = name_policy or CharacterNamePolicy()

    async def list_generation_options(self, *, limit: int = 100) -> AdminPlayerGenerationOptionsResponseDTO:
        clans = await self.monster_repo.list_generated_clans(limit=limit)
        options = [_clan_option(clan) for clan in clans]
        return AdminPlayerGenerationOptionsResponseDTO(
            clans=[option for option in options if option.can_generate_player_equipment]
        )

    async def generate_for_user(
        self,
        user_id: UUID,
        request: AdminPlayerGenerateCharacterRequestDTO,
    ) -> AdminPlayerGenerateCharacterResponseDTO:
        await self._ensure_slot_available(user_id)
        source_clan = await self._load_source_clan(request.source_clan_id)
        name = await self._resolve_name(request, source_clan.family_id)
        gender = _resolve_gender(request.gender, seed=f"{user_id}:{name.key}:{request.slot_index}")
        avatar_url = (
            "/static/images/avatars/silhouette_f.webp"
            if gender == "female"
            else "/static/images/avatars/silhouette_m.webp"
        )
        character = await self.character_repo.create_with_defaults(
            user_id=user_id,
            name=name.display,
            name_key=name.key,
            gender=gender,
            avatar_url=avatar_url,
            game_stage=CoreDomain.LOBBY.value,
            prev_game_stage=None,
            location_id=self.INITIAL_LOCATION_ID,
        )
        char_id = int(character.character_id)

        await self.attributes_repo.upsert_attributes(char_id, _random_attributes(f"{user_id}:{char_id}:{name.key}"))
        await self.progression_repo.set_free_xp(char_id, 0.0)
        skill_keys = _skill_keys_for_family(source_clan.family_id)
        await self.skill_repo.unlock_skills(
            char_id,
            skill_keys,
            progress_state=SkillProgressState.PLUS,
            initial_xp=float(request.skill_progress_percent) / 100.0,
        )
        generated_item_ids, variant_id = await self._generate_family_loadout(char_id, request, source_clan)
        await self.character_repo.commit()
        logger.bind(
            user_id=str(user_id),
            char_id=char_id,
            family_id=source_clan.family_id,
            item_count=len(generated_item_ids),
        ).info("AdminTestCharacterGenerated")
        return AdminPlayerGenerateCharacterResponseDTO(
            character=_character_summary(character),
            generated_item_ids=generated_item_ids,
            family_id=source_clan.family_id,
            source_clan_id=str(source_clan.id),
            variant_id=variant_id,
            item_tier=request.item_tier,
            skill_progress_percent=request.skill_progress_percent,
        )

    async def _load_source_clan(self, source_clan_id: str):
        source_clan = await self.monster_repo.get_generated_clan(source_clan_id)
        if source_clan is None:
            raise BusinessLogicException("Сгенерированная семья не найдена")
        option = _clan_option(source_clan)
        if not option.can_generate_player_equipment:
            raise BusinessLogicException(option.reason or "Семья не подходит для экипировки игрока")
        return source_clan

    async def _ensure_slot_available(self, user_id: UUID) -> None:
        count = await self.character_repo.count_by_user_id(user_id)
        if count >= self.MAX_SLOTS:
            raise BusinessLogicException("Лимит персонажей достигнут")

    async def _resolve_name(self, request: AdminPlayerGenerateCharacterRequestDTO, family_id: str):
        raw_name = request.name.strip() or _generated_name(family_id, request.slot_index)
        try:
            name = self.name_policy.validate(raw_name)
        except CharacterNameError as exc:
            raise BusinessLogicException(exc.message) from exc
        if not await self.character_repo.exists_by_name_key(name.key):
            return name
        if request.name.strip():
            raise BusinessLogicException("Имя уже занято")
        for suffix in range(2, 50):
            candidate = self.name_policy.validate(f"{raw_name} {suffix}")
            if not await self.character_repo.exists_by_name_key(candidate.key):
                return candidate
        raise BusinessLogicException("Не удалось подобрать свободное имя")

    async def _generate_family_loadout(
        self,
        char_id: int,
        request: AdminPlayerGenerateCharacterRequestDTO,
        source_clan: Any,
    ) -> tuple[list[str], str]:
        family = get_family_config(source_clan.family_id)
        if family is None:
            raise BusinessLogicException("Неизвестное семейство предметов")
        source_member = _select_source_member(source_clan, request.item_tier)
        variant_id = (
            source_member.variant_key if source_member is not None else _select_variant_id(family.id, request.item_tier)
        )
        variant = family.variants[variant_id]
        loadout = _loadout_for_variant(variant)
        generated_item_ids: list[str] = []
        for index, (slot, equipment_key) in enumerate(loadout.items(), start=1):
            is_natural = _is_natural_equipment(equipment_key)
            build_request = build_monster_item_request(
                owner_key=f"admin-test-character:{char_id}",
                family_id=family.id,
                member_role=variant.role,
                member_tier=request.item_tier,
                slot=slot,
                natural_key=equipment_key if is_natural else None,
                base_id=None if is_natural else equipment_key,
                item_kind=_item_kind(slot),
                item_grade="artifact" if request.item_tier >= 4 else "",
                rarity_tier=request.item_tier,
                seed=f"admin:test-character:{char_id}:{slot}:{equipment_key}:{index}",
                source_context={
                    "admin_generation": True,
                    "character_id": char_id,
                    "slot_index": request.slot_index,
                    "family_id": family.id,
                    "source_clan_id": str(source_clan.id),
                    "source_clan_name": source_clan.name_ru,
                    "source_clan_tier": source_clan.tier,
                    "source_clan_zone_id": source_clan.zone_id or "",
                    "source_clan_unique_hash": source_clan.unique_hash,
                    "variant_id": variant_id,
                    **dict(source_clan.source_context or {}),
                },
            )
            item_request = to_item_generation_request(build_request).model_copy(
                update={
                    "generation_mode": "player",
                    "char_id": char_id,
                    "request_ai_text": request.request_ai_text,
                    "source": "admin:test_character_generation",
                    "placement_ref": ItemPlacementRefDTO(
                        holder_type="character",
                        holder_id=str(char_id),
                        storage_type="equipped",
                        slot=slot,
                    ),
                    "origin_ref": ItemOriginRefDTO(
                        origin_type="admin",
                        origin_ref="admin:test_character_generation",
                        seed=f"admin:test-character:{char_id}:{slot}:{equipment_key}:{request.item_tier}",
                    ),
                }
            )
            result = await self.item_generation.generate_mechanical(item_request)
            generated_item_ids.extend(result.item_ids)
        return generated_item_ids, variant_id


def _random_attributes(seed: str) -> dict[str, int]:
    rng = random.Random(seed)
    values = {key: 8 for key in _ATTRIBUTE_KEYS}
    for _ in range(9):
        values[rng.choice(_ATTRIBUTE_KEYS)] += 1
    return values


def _resolve_gender(raw: str, *, seed: str) -> str:
    if raw in {"male", "female", "other"}:
        return raw
    return random.Random(seed).choice(["male", "female", "other"])


def _generated_name(family_id: str, slot_index: int) -> str:
    prefix = family_id.replace("_", " ").title().replace(" ", "")
    return f"Test_{prefix}_{slot_index}"


def _skill_keys_for_family(family_id: str) -> list[str]:
    family = get_family_config(family_id)
    skills = list(_BASE_SKILLS)
    if family:
        for variant in family.variants.values():
            skills.extend(variant.skills)
    return list(dict.fromkeys(skills))


def _clan_option(clan: Any) -> AdminPlayerGenerationClanOptionDTO:
    family = get_family_config(clan.family_id)
    can_generate, reason = _can_generate_player_equipment(family)
    label = str(clan.name_ru or clan.family_id)
    if clan.zone_id:
        label = f"{label} / {clan.zone_id}"
    return AdminPlayerGenerationClanOptionDTO(
        clan_id=str(clan.id),
        label=label,
        family_id=str(clan.family_id),
        tier=int(clan.tier or 0),
        zone_id=clan.zone_id,
        can_generate_player_equipment=can_generate,
        reason=reason,
    )


def _can_generate_player_equipment(family: Any | None) -> tuple[bool, str]:
    if family is None:
        return False, "Неизвестное семейство"
    loot = family.loot_profile
    if loot is None:
        return False, "У семейства нет loot_profile"
    if loot.allowed_loadout_slots != "full_humanoid":
        return False, "Семейство не использует humanoid equipment slots"
    if loot.equipment_drop_policy != "fixed_loadout":
        return False, "Семейство не имеет fixed_loadout"
    if not loot.drops_as_equipment:
        return False, "Семейство не дропает экипировку"
    if loot.loot_mode not in {"equipment", "hybrid"}:
        return False, "Семейство не в equipment/hybrid loot mode"
    return True, ""


def _select_source_member(clan: Any, requested_tier: int) -> Any | None:
    members = list(getattr(clan, "members", None) or [])
    if not members:
        return None
    role_order = _role_preference(requested_tier)
    for role in role_order:
        role_members = [member for member in members if member.role == role]
        if role_members:
            return sorted(role_members, key=lambda member: abs(int(member.member_tier or 0) - requested_tier))[0]
    return members[0]


def _select_variant_id(family_id: str, tier: int) -> str:
    family = get_family_config(family_id)
    if family is None:
        raise BusinessLogicException("Неизвестное семейство предметов")
    candidates = get_available_variants_for_tier_window(family_id, tier, radius=1)
    if not candidates:
        candidates = list(family.variants)
    role_order = _role_preference(tier)
    for role in role_order:
        for variant_id in candidates:
            if family.variants[variant_id].role == role:
                return variant_id
    return candidates[0]


def _role_preference(tier: int) -> tuple[str, ...]:
    if tier >= 6:
        return ("boss", "elite", "veteran", "minion")
    if tier >= 4:
        return ("elite", "veteran", "minion", "boss")
    if tier >= 2:
        return ("veteran", "minion", "elite", "boss")
    return ("minion", "veteran", "elite", "boss")


def _loadout_for_variant(variant: Any) -> dict[str, str]:
    variant_loadout = variant.fixed_loadout.model_dump(exclude_none=True)
    loadout = {**_FULL_LOADOUT, **{str(slot): str(base_id) for slot, base_id in variant_loadout.items() if base_id}}
    if loadout.get("two_hand"):
        loadout.pop("main_hand", None)
        loadout.pop("off_hand", None)
    return loadout


def _is_natural_equipment(equipment_key: str) -> bool:
    try:
        get_natural_equipment_mapping(equipment_key)
    except ValueError:
        return False
    return True


def _item_kind(slot: str) -> MonsterItemAffixKind:
    if slot == "off_hand":
        return "shield"
    if slot.endswith("_armor") or slot in {
        "feetwear",
        "chest_garment",
        "legs_garment",
        "outer_garment",
        "gloves_garment",
    }:
        return "armor"
    return "weapon"

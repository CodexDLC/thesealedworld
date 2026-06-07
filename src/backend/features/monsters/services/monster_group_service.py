from __future__ import annotations

import random
import uuid
from typing import TYPE_CHECKING, Any

from src.backend.features.monsters.dto.generation import (
    GeneratedClan,
    GeneratedMonster,
    MonsterGenerationContext,
    MonsterGroupMemberPreview,
    MonsterGroupResult,
)
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.visuals import version_generated_asset_url, version_visual_image_urls
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder
from src.backend.features.monsters.runtime.encounter_profiles import get_monster_encounter_profile
from src.backend.features.monsters.runtime.group_assembler import MonsterGroupAssembler
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService

if TYPE_CHECKING:
    from src.backend.features.monsters.integrations import (
        MonsterActorCommitmentIntegration,
        MonsterGenerationStorage,
        MonsterLocationContextIntegration,
    )
    from src.backend.features.monsters.runtime.clan_factory import ClanFactory
    from src.backend.infrastructure.monsters.managers import MonsterGroupCacheManager


_ENCOUNTER_KIND_ALIASES = {
    "ordinary": "ordinary",
    "ordinary_node": "ordinary",
    "transition": "ordinary",
    "node_event": "guard",
    "key_guard": "guard",
    "guard": "guard",
    "heart_guard": "boss",
    "boss": "boss",
    "boss_solo": "boss",
    "boss_with_minions": "boss",
}
_ENCOUNTER_DIFFICULTY_ALIASES = {
    "easy": "easy",
    "light": "easy",
    "low": "easy",
    "normal": "normal",
    "medium": "normal",
    "mid": "normal",
    "hard": "hard",
    "heavy": "hard",
    "high": "hard",
}
_PROFILE_POLICY_KEYS = {
    "budget_multiplier",
    "min_units",
    "max_units",
    "start_role",
    "allowed_roles",
    "required_roles",
    "role_caps",
    "upgrade_order",
    "allow_repeated_members",
    "prefer_distinct_members",
}


class MonsterGroupService:
    def __init__(
        self,
        *,
        repository: MonsterGenerationStorage,
        location_context: MonsterLocationContextIntegration,
        actor_commitments: MonsterActorCommitmentIntegration,
        group_cache: MonsterGroupCacheManager | None = None,
        factory: ClanFactory,
        assembler: MonsterGroupAssembler | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.repository = repository
        self.location_context = location_context
        self.actor_commitments = actor_commitments
        self.group_cache = group_cache
        self.factory = factory
        self.assembler = assembler or MonsterGroupAssembler()
        self.actor_builder = MonsterCombatActorInputBuilder()
        self.gear_score_service = MonsterGearScoreService()
        self._rng = rng or random.Random()  # nosec B311

    async def prepare_monster_group(
        self,
        loc_id: str,
        budget: float,
        preferred_family_id: str | None = None,
        force_single_family: bool = True,
        threat_mitigation_skill: float = 0.0,
        *,
        scope_id: str | None = None,
        ttl: int = 300,
        composition_policy: dict[str, Any] | None = None,
    ) -> MonsterGroupResult:
        location = await self.location_context.get_location_context(loc_id)
        group_scope_id = scope_id
        scope_type = "region"
        pool_scope_id = self._location_region_id(location.raw_location)
        clan, reused_existing_clan, pool_tags = await self._resolve_clan_from_pool(
            scope_type=scope_type,
            scope_id=pool_scope_id,
            preferred_family_id=preferred_family_id,
        )
        return await self._prepare_group_from_clan(
            clan=clan,
            budget=budget,
            tier=location.tier,
            danger=location.danger,
            loc_id=location.loc_id,
            zone_id=location.zone_id,
            biome_id=location.biome_id,
            context_hash=clan.context_hash,
            tags=pool_tags,
            reused_existing_clan=reused_existing_clan,
            force_single_family=force_single_family,
            threat_mitigation_skill=threat_mitigation_skill,
            composition_policy=self._location_composition_policy(location.raw_location, composition_policy),
            scope_id=group_scope_id,
            ttl=ttl,
        )

    async def prepare_monster_group_for_hash_context(
        self,
        *,
        family_id: str,
        hash_context: Any,
        generation_context: MonsterGenerationContext,
        budget: float,
        tier: int,
        danger: float,
        biome_id: str,
        loc_id: str,
        zone_id: str | None = None,
        tags: list[str] | None = None,
        force_single_family: bool = True,
        composition_policy: dict[str, Any] | None = None,
        scope_id: str | None = None,
        ttl: int = 300,
    ) -> MonsterGroupResult:
        raise RuntimeError("Hash-context monster group preparation was replaced by habitat clan pool lookup")

    async def prepare_monster_group_for_scope(
        self,
        *,
        scope_type: str,
        scope_id: str,
        budget: float,
        tier: int,
        danger: float,
        biome_id: str,
        loc_id: str,
        zone_id: str | None = None,
        preferred_family_id: str | None = None,
        force_single_family: bool = True,
        threat_mitigation_skill: float = 0.0,
        composition_policy: dict[str, Any] | None = None,
        group_scope_id: str | None = None,
        ttl: int = 300,
    ) -> MonsterGroupResult:
        clan, reused_existing_clan, pool_tags = await self._resolve_clan_from_pool(
            scope_type=scope_type,
            scope_id=scope_id,
            preferred_family_id=preferred_family_id,
        )

        return await self._prepare_group_from_clan(
            clan=clan,
            budget=budget,
            tier=tier,
            danger=danger,
            loc_id=loc_id,
            zone_id=zone_id,
            biome_id=biome_id,
            context_hash=clan.context_hash,
            tags=pool_tags,
            reused_existing_clan=reused_existing_clan,
            force_single_family=force_single_family,
            threat_mitigation_skill=threat_mitigation_skill,
            composition_policy=composition_policy,
            scope_id=group_scope_id,
            ttl=ttl,
        )

    async def _prepare_group_from_clan(
        self,
        *,
        clan: GeneratedClan,
        budget: float,
        tier: int,
        danger: float,
        loc_id: str,
        zone_id: str | None,
        biome_id: str,
        context_hash: str,
        tags: list[str],
        reused_existing_clan: bool,
        force_single_family: bool,
        threat_mitigation_skill: float,
        composition_policy: dict[str, Any] | None,
        scope_id: str | None,
        ttl: int,
    ) -> MonsterGroupResult:
        members = await self._fresh_clan_members(clan.id)
        if not members:
            members = list(clan.members)
        for member in members:
            if member.clan is None:
                member.clan = clan
        members = self._members_for_effective_tier(clan.family_id, members, tier=tier)
        members = [self._select_tier_snapshot(member, tier=tier) for member in members]
        effective_policy = self._profile_composition_policy(
            clan=clan,
            members=members,
            budget=budget,
            tier=tier,
            tags=tags,
            composition_policy=composition_policy,
        )
        assembly_danger = _mitigated_danger(danger, threat_mitigation_skill)
        assembly = self.assembler.assemble(
            members,
            budget=budget,
            tier=tier,
            danger=assembly_danger,
            force_single_family=force_single_family,
            composition_policy=effective_policy,
        )
        if not assembly.members:
            raise ValueError(f"No generated monsters available for clan={clan.id}")

        group_id = scope_id or f"monster_group:{uuid.uuid4()}"
        sources = [self._materialize_actor_source(member) for member in assembly.members]
        actor_commitments = await self.actor_commitments.save_monster_sources(
            sources=sources,
            ttl=ttl,
        )
        expected_source_refs = {f"monster:{source['source']['monster_id']}" for source in sources}
        if set(actor_commitments) != expected_source_refs:
            raise RuntimeError("Failed to save all monster actor commitments")

        previews = [self._preview(member) for member in assembly.members]
        result = MonsterGroupResult(
            group_id=group_id,
            clan_id=str(clan.id),
            family_id=clan.family_id,
            loc_id=loc_id,
            zone_id=zone_id,
            biome_id=biome_id,
            tier=tier,
            danger=danger,
            target_budget=assembly.target_budget,
            adjusted_budget=assembly.adjusted_budget,
            total_power=assembly.total_power,
            monster_ids=[str(member.id) for member in assembly.members],
            actor_commitments=actor_commitments,
            encounter_texts={str(key): str(value) for key, value in clan.encounter_texts.items() if value},
            previews=previews,
            reused_existing_clan=reused_existing_clan,
            context_hash=context_hash,
            unique_hash=clan.identity_hash,
            tags=tags,
        )

        if self.group_cache is not None:
            group_key = await self.group_cache.save_group(
                group_id,
                self._group_payload(result),
                ttl=ttl,
            )
            result.group_key = group_key
        return result

    async def _resolve_clan_from_pool(
        self,
        *,
        scope_type: str,
        scope_id: str,
        preferred_family_id: str | None,
    ) -> tuple[GeneratedClan, bool, list[str]]:
        entries = await self.repository.list_habitat_clan_pool_entries(
            scope_type=scope_type,
            scope_id=scope_id,
            enabled_only=True,
        )
        if preferred_family_id:
            entries = [entry for entry in entries if entry.family_id == preferred_family_id]
        if not entries:
            raise ValueError(f"No materialized monster clan pool for {scope_type}={scope_id}")
        entry = self._weighted_pool_entry(entries)
        clan = await self.repository.get_clan_by_identity_hash(entry.clan_identity_hash)
        if clan is None:
            raise ValueError(f"Habitat clan pool points to missing clan: {entry.clan_identity_hash}")
        return clan, True, [entry.habitat.biome, *entry.habitat.keys]

    def _weighted_pool_entry(self, entries):
        total = sum(max(0, int(entry.weight)) for entry in entries)
        if total <= 0:
            return sorted(entries, key=lambda entry: (entry.pool_tier, entry.family_id, entry.clan_identity_hash))[0]
        roll = self._rng.uniform(0, total)
        upto = 0.0
        for entry in sorted(
            entries, key=lambda item: (item.pool_tier != "primary", item.family_id, item.clan_identity_hash)
        ):
            upto += max(0, int(entry.weight))
            if roll <= upto:
                return entry
        return entries[-1]

    async def _fresh_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]:
        members = await self.repository.get_clan_members(clan_id)
        return members

    @staticmethod
    def _location_region_id(raw_location: dict[str, Any]) -> str:
        world_zone = raw_location.get("world_zone")
        if isinstance(world_zone, dict) and world_zone.get("region_id"):
            return str(world_zone["region_id"])
        region_id = raw_location.get("region_id")
        if region_id:
            return str(region_id)
        raise ValueError("World location is missing region_id for monster clan pool lookup")

    def _choose_existing_clan(self, clans: list[GeneratedClan]) -> GeneratedClan:
        return self._rng.choice(sorted(clans, key=lambda clan: clan.identity_hash))

    @staticmethod
    def _members_for_effective_tier(
        family_id: str,
        members: list[GeneratedMonster],
        *,
        tier: int,
    ) -> list[GeneratedMonster]:
        del family_id
        effective_tier = max(0, min(11, int(tier)))
        return [member for member in members if member.min_tier <= effective_tier <= member.max_tier]

    def _profile_composition_policy(
        self,
        *,
        clan: GeneratedClan,
        members: list[GeneratedMonster],
        budget: float,
        tier: int,
        tags: list[str],
        composition_policy: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        raw_policy = dict(composition_policy or {})
        kind = _encounter_kind(raw_policy, tags)
        difficulty = self._encounter_difficulty(raw_policy, members=members, budget=budget, tier=tier)
        profile = get_monster_encounter_profile(clan.family_id, kind, difficulty)
        if profile is None:
            return raw_policy or None

        profile_policy: dict[str, Any] = dict(profile)
        profile_policy["encounter_kind"] = kind
        profile_policy["encounter_difficulty"] = difficulty
        return _merge_profile_policy(profile_policy, raw_policy)

    def _encounter_difficulty(
        self,
        policy: dict[str, Any],
        *,
        members: list[GeneratedMonster],
        budget: float,
        tier: int,
    ) -> str:
        explicit = _normalize_encounter_difficulty(policy.get("encounter_difficulty") or policy.get("difficulty"))
        if explicit is not None:
            return explicit

        expected = _family_expected_gear_score(members, tier=tier)
        ratio = float(budget) / expected if expected > 0 else 1.0
        return self._weighted_difficulty(ratio)

    def _weighted_difficulty(self, power_ratio: float) -> str:
        if power_ratio < 2.0:
            weights = {"easy": 75, "normal": 25, "hard": 0}
        elif power_ratio < 3.0:
            weights = {"easy": 35, "normal": 50, "hard": 15}
        else:
            weights = {"easy": 0, "normal": 25, "hard": 75}
        return _weighted_choice(weights, self._rng)

    @staticmethod
    def _context_meta(raw_location: dict) -> dict[str, object]:
        flags = raw_location.get("flags")
        if not isinstance(flags, dict):
            return {}
        result: dict[str, object] = {}
        rift_profile = flags.get("rift_profile")
        if isinstance(rift_profile, dict):
            result["rift_profile"] = rift_profile
        for key in ("encounter_kind", "encounter_difficulty", "difficulty"):
            value = flags.get(key)
            if value:
                result[key] = str(value)
        return result

    @staticmethod
    def _location_composition_policy(
        raw_location: dict[str, Any],
        composition_policy: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        flags = raw_location.get("flags")
        if not isinstance(flags, dict):
            return composition_policy
        location_policy: dict[str, Any] = {}
        for key in ("encounter_kind", "encounter_difficulty", "difficulty"):
            value = flags.get(key)
            if value:
                location_policy[key] = str(value)
        if not location_policy:
            return composition_policy
        return {**location_policy, **dict(composition_policy or {})}

    def _materialize_actor_source(self, monster: GeneratedMonster) -> dict[str, object]:
        return self.actor_builder.build_snapshot(monster)

    def _preview(self, monster: GeneratedMonster) -> MonsterGroupMemberPreview:
        family_id = monster.family_id
        family = get_family_config(family_id) if family_id else None
        tags = ["monster", monster.role]
        if family is not None:
            tags.extend([family.id, family.archetype, *family.default_tags])
        visual = version_visual_image_urls(self._monster_visual(monster))
        return MonsterGroupMemberPreview(
            monster_id=str(monster.id),
            name=monster.title,
            description=monster.short_description,
            role=monster.role,
            variant_key=monster.variant_id,
            member_tier=self._snapshot_tier(monster),
            threat_rating=self._gear_score(monster) or 1,
            hp=dict((monster.active_snapshot.get("combat_snapshot_input") or {}).get("status", {}).get("hp") or {}),
            image=self._visual_image_url(visual),
            visual=visual,
            tags=sorted(set(tags)),
            archetype=family.archetype if family is not None else None,
            family_id=family_id,
            organization_type=self._organization_type(monster, family=family),
            gear_score=self._gear_score(monster),
            vitals=self._preview_vitals(monster),
            equipment=self._preview_equipment(monster),
            affixes=self._preview_affixes(monster),
        )

    @staticmethod
    def _monster_visual(monster: GeneratedMonster) -> dict[str, Any]:
        # Single source of truth: PG ``metadata_["visual"]``. AI-таска пишет сюда
        # после успешной генерации (см. ``tasks_ai.py``). Mongo ``base_projection.visual``
        # больше не читаем — оно остаётся в коллекции как мёртвый legacy-снимок
        # placeholder'а от момента создания клана.
        visual = monster.metadata_.get("visual") if isinstance(monster.metadata_, dict) else None
        return dict(visual) if isinstance(visual, dict) else {}

    @staticmethod
    def _visual_image_url(visual: dict[str, Any]) -> str | None:
        # Single field: ``image_url``. До AI-генерации = family placeholder,
        # после AI = реальный сгенерированный URL. Фронту больше не нужно
        # перебирать каскад полей и угадывать какое из них главное.
        value = visual.get("image_url")
        if not value:
            return None
        return version_generated_asset_url(str(value), visual)

    @staticmethod
    def _organization_type(monster: GeneratedMonster, *, family: Any | None) -> str | None:
        return str(family.organization_type) if family is not None else None

    @staticmethod
    def _gear_score(monster: GeneratedMonster) -> int | None:
        value = dict(monster.active_snapshot or {}).get("gear_score")
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _select_tier_snapshot(monster: GeneratedMonster, *, tier: int) -> GeneratedMonster:
        actor_document = monster.actor_document if isinstance(monster.actor_document, dict) else {}
        snapshots = actor_document.get("tier_snapshots")
        if not isinstance(snapshots, dict):
            raise ValueError(f"Generated monster actor document has no tier_snapshots: {monster.mongo_actor_key}")
        key = f"tier_{int(tier)}"
        snapshot = snapshots.get(key)
        if not isinstance(snapshot, dict):
            raise ValueError(
                f"Missing generated monster tier snapshot actor={monster.mongo_actor_key} effective_tier={key}"
            )
        monster.active_snapshot = dict(snapshot)
        return monster

    @staticmethod
    def _snapshot_tier(monster: GeneratedMonster) -> int:
        value = dict(monster.active_snapshot or {}).get("effective_tier")
        try:
            return int(value)
        except (TypeError, ValueError):
            return monster.min_tier

    @staticmethod
    def _preview_vitals(monster: GeneratedMonster) -> dict[str, Any]:
        raw = dict((monster.active_snapshot.get("combat_snapshot_input") or {}).get("status") or {})
        return {
            "hp": dict(raw.get("hp") or {}),
            "energy": dict(raw.get("energy") or raw.get("en") or {}),
            "concentration": dict(raw.get("concentration") or raw.get("stamina") or {}),
        }

    @staticmethod
    def _preview_equipment(monster: GeneratedMonster) -> list[dict[str, Any]]:
        items = dict(monster.active_snapshot.get("items") or {})
        layout = dict(items.get("layout") or {})
        equipment = dict(layout.get("equipment") or {})
        by_id = dict(items.get("by_id") or {})
        rows: list[dict[str, Any]] = []
        for slot, item_id in equipment.items():
            item = by_id.get(str(item_id))
            if not isinstance(item, dict):
                continue
            combat = dict(item.get("combat") or {})
            rows.append(
                {
                    "slot": str(slot),
                    "kind": str(item.get("item_type") or "item"),
                    "label": str(item.get("base_id") or item_id),
                    "item_id": str(item_id),
                    "tags": [str(tag) for tag in combat.get("tags", []) if tag]
                    if isinstance(combat.get("tags"), list)
                    else [],
                }
            )
        return rows

    @staticmethod
    def _preview_affixes(monster: GeneratedMonster) -> list[dict[str, Any]]:
        return [dict(affix) for affix in monster.active_snapshot.get("affixes", []) if isinstance(affix, dict)]

    @staticmethod
    def _group_payload(result: MonsterGroupResult) -> dict[str, object]:
        return result.model_dump(mode="json", exclude={"group_key"})


def _encounter_kind(policy: dict[str, Any], tags: list[str]) -> str:
    for value in (
        policy.get("encounter_kind"),
        policy.get("kind"),
        policy.get("event_scope"),
        policy.get("rift_event_scope"),
    ):
        normalized = _normalize_encounter_kind(value)
        if normalized is not None:
            return normalized
    for tag in tags:
        normalized = _normalize_encounter_kind(tag)
        if normalized is not None:
            return normalized
    return "ordinary"


def _normalize_encounter_kind(value: Any) -> str | None:
    key = str(value or "").strip()
    return _ENCOUNTER_KIND_ALIASES.get(key)


def _normalize_encounter_difficulty(value: Any) -> str | None:
    key = str(value or "").strip()
    return _ENCOUNTER_DIFFICULTY_ALIASES.get(key)


def _merge_profile_policy(profile_policy: dict[str, Any], explicit_policy: dict[str, Any]) -> dict[str, Any]:
    result = dict(profile_policy)
    for key, value in explicit_policy.items():
        if key in _PROFILE_POLICY_KEYS or key not in {"encounter_kind", "encounter_difficulty"}:
            result[key] = value
    return result


def _family_expected_gear_score(members: list[GeneratedMonster], *, tier: int) -> float:
    """Raw family baseline for player/party difficulty comparisons.

    This must not use balance.gear_score or balance.assembly_cost: those values
    are organization-divided member costs for pack assembly only.
    """
    del tier
    scores = [score for member in members if (score := _member_raw_gear_score(member)) is not None]
    if not scores:
        return 1.0
    return max(1.0, sum(scores) / len(scores))


def _member_raw_gear_score(member: GeneratedMonster) -> int | None:
    value = dict(member.active_snapshot or {}).get("raw_gear_score")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _weighted_choice(weights: dict[str, int], rng: random.Random) -> str:
    total = sum(max(0, weight) for weight in weights.values())
    if total <= 0:
        return "normal"
    roll = rng.uniform(0, total)
    upto = 0.0
    for value, weight in weights.items():
        upto += max(0, weight)
        if roll <= upto:
            return value
    return "normal"


def _mitigated_danger(danger: float, skill_value: Any) -> float:
    return max(0.0, float(danger) - _normalized_skill(skill_value))


def _normalized_skill(value: Any) -> float:
    try:
        raw = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if raw > 1.0:
        raw /= 100.0
    return max(0.0, min(1.0, raw))

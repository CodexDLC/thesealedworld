from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from src.backend.features.character.resources import CHARACTER_ATTRIBUTE_TEXT
from src.backend.features.game_catalog.combat.resources import CombatResourceCatalogService
from src.backend.features.game_catalog.dto import GameCatalogBootstrapDTO, GameCatalogManifestDTO
from src.backend.features.game_catalog.skills.services import SkillCatalogService
from src.backend.features.items.services import ItemCatalogService
from src.backend.features.monsters.resources import get_all_family_configs
from src.backend.features.monsters.resources.visuals import get_family_visual

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster


class GameCatalogBootstrapService:
    VERSION = "game-catalog:2026-05-07.1"

    def __init__(
        self,
        *,
        skills: SkillCatalogService | None = None,
        items: ItemCatalogService | None = None,
        combat: CombatResourceCatalogService | None = None,
    ) -> None:
        self.skills = skills or SkillCatalogService()
        self.items = items or ItemCatalogService.load_default()
        self.combat = combat or CombatResourceCatalogService.load_default()

    def build_bootstrap(self) -> GameCatalogBootstrapDTO:
        catalogs = {
            "items": self.items.all_public_text(),
            "skills": self.skills.all_public_text(),
            "attributes": CHARACTER_ATTRIBUTE_TEXT,
            "monster_families": self.build_monster_families_catalog(),
            **self.combat.all_public_text(),
        }
        return GameCatalogBootstrapDTO(
            version=self.VERSION,
            catalogs=catalogs,
            manifest=GameCatalogManifestDTO(
                version=self.VERSION,
                catalogs={name: self._hash(payload) for name, payload in catalogs.items()},
            ),
        )

    @staticmethod
    def _hash(payload: object) -> str:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return f"sha256:{hashlib.sha256(data).hexdigest()}"

    def build_monster_families_catalog(self) -> dict[str, dict[str, object]]:
        families: dict[str, dict[str, object]] = {}
        for family_id, family in sorted(get_all_family_configs().items()):
            variants = sorted(family.variants.values(), key=lambda item: (item.role, item.min_tier, item.id))
            tier_min = min((variant.min_tier for variant in variants), default=0)
            tier_max = max((variant.max_tier for variant in variants), default=0)
            role_counts: dict[str, int] = {}
            for variant in variants:
                role_counts[variant.role] = role_counts.get(variant.role, 0) + 1

            families[family_id] = {
                "id": family_id,
                "title": _title_from_id(family_id),
                "archetype": family.archetype,
                "organization_type": family.organization_type,
                "tags": family.default_tags,
                "tier_min": tier_min,
                "tier_max": tier_max,
                "role_counts": role_counts,
                "loot_mode": family.loot_profile.loot_mode if family.loot_profile else "none",
                "salvage_type": family.loot_profile.salvage_type if family.loot_profile else None,
                "visual": get_family_visual(family_id),
                "variant_count": len(variants),
                "variants": [
                    {
                        "id": variant.id,
                        "title": _title_from_id(variant.id),
                        "role": variant.role,
                        "tier_min": variant.min_tier,
                        "tier_max": variant.max_tier,
                        "cost": variant.cost,
                        "tags": variant.extra_tags,
                        "skills": sorted(variant.skill_overrides),
                        "description": variant.narrative_hint,
                        "visual": get_family_visual(family_id),
                    }
                    for variant in variants
                ],
            }
        return families

    def project_generated_monster_clans(self, clans: list[GeneratedClan]) -> list[dict[str, object]]:
        return [
            {
                "id": str(clan.id),
                "title": _public_clan_title(clan),
                "family_key": clan.family_id,
                "family_label": _public_family_label(clan),
                "description": clan.description,
                "summary": _public_clan_summary(clan),
                "habitat": _public_habitat(clan),
                "location_key": _public_location_key(clan),
                "location_label": _public_habitat(clan),
                "danger": _public_danger(clan.tier),
                "danger_key": _public_danger_key(clan.tier),
                "visual": _public_clan_visual(clan),
                "tier": clan.tier,
                "filter_tags": _public_filter_tags(clan),
                "member_count": len(clan.members),
                "members": [self._project_generated_member(member) for member in clan.members],
            }
            for clan in clans
        ]

    def _project_generated_member(self, member: GeneratedMonster) -> dict[str, object]:
        return {
            "id": str(member.id),
            "title": _clean_generated_title(member.name_ru or _title_from_id(member.variant_key)),
            "description": _public_member_description(member),
            "role_label": _ROLE_LABELS.get(member.role, _title_from_id(member.role)),
            "danger": _public_member_danger(member.threat_rating),
            "visual": _public_member_visual(member),
            "public_stats": _public_stats(member.scaled_attributes),
            "public_loadout": _public_loadout(member.items),
            "public_skills": _public_skills(member.scaled_skills),
        }


def _title_from_id(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def _tags_from_raw(raw_tags: dict[str, object]) -> list[str]:
    tags: list[str] = []
    for key, value in raw_tags.items():
        if isinstance(value, str):
            tags.append(value)
        elif isinstance(value, list):
            tags.extend(str(item) for item in value if item)
        elif value is True:
            tags.append(key)
    return sorted(set(tags))


_FAMILY_TITLES = {
    "bandit_gang": "Roadside Cutthroats",
    "goblin_tribe": "Gutter Goblins",
    "rat_swarm": "Ruin Rats",
    "wolf_pack": "Ashen Wolves",
}

_FAMILY_SUMMARIES = {
    "bandit_gang": "Human raiders working the broken roads and abandoned streets. They favor ambushes, dirty blades, and quick retreats.",
    "goblin_tribe": "Small scavengers nesting in cracks of the old district. They are weak alone, but dangerous when they gather around a loud leader.",
    "rat_swarm": "Disease-bearing vermin moving through cellars, drains, and collapsed alleys. The threat is not one bite, but the swarm closing in.",
    "wolf_pack": "Lean predators drawn to the edge of the ruins. They test prey with feints, circle wide, and strike when someone falls behind.",
}

_TAG_LABELS = {
    "city_ruins": "city ruins",
    "forest": "wild growth",
    "mid": "steady activity",
    "low": "scattered signs",
    "high": "heavy presence",
    "wasteland": "wasteland",
    "unnatural_chill": "unnatural chill",
    "hoarfrost_on_runes": "frosted runes",
    "frozen_dew": "frozen dew",
    "thin_ice_crust": "thin ice",
    "ice_shards": "ice shards",
    "heat_haze": "heat haze",
    "smell_of_sulfur": "sulfur",
    "falling_ash": "falling ash",
    "scorched_grass": "scorched grass",
    "static_tingle": "static charge",
    "dust_motes_hovering": "hovering dust",
    "floating_pebbles": "floating stones",
    "spores_in_light": "spores",
    "accelerated_growth": "wild growth",
    "mossy_patches": "moss",
    "glowing_fungi": "glowing fungi",
    "cursed_ground": "cursed ground",
    "ancient_tech": "ancient tech",
    "mana_leak": "mana leak",
}

_ROLE_LABELS = {
    "minion": "Common form",
    "veteran": "Seasoned form",
    "elite": "Dangerous form",
    "boss": "Leader",
}

_STAT_LABELS = {
    "strength": "Strength",
    "agility": "Agility",
    "endurance": "Endurance",
    "intellect": "Intellect",
    "memory": "Instinct",
    "mental": "Will",
    "perception": "Senses",
    "projection": "Presence",
    "prediction": "Luck",
}

_LOADOUT_LABELS = {
    "main_hand": "Main hand",
    "off_hand": "Off hand",
    "head_armor": "Head",
    "chest_armor": "Armor",
    "arms_armor": "Arms",
    "legs_armor": "Legs",
    "feetwear": "Footwear",
    "chest_garment": "Garment",
    "legs_garment": "Legwear",
    "outer_garment": "Outerwear",
    "gloves_garment": "Gloves",
    "amulet": "Amulet",
    "ring_1": "Ring",
    "ring_2": "Ring",
    "belt_accessory": "Belt",
}


def _public_clan_title(clan: GeneratedClan) -> str:
    if clan.family_id in _FAMILY_TITLES:
        return _FAMILY_TITLES[clan.family_id]
    return _clean_generated_title(clan.name_ru or _title_from_id(clan.family_id))


def _public_family_label(clan: GeneratedClan) -> str:
    return _FAMILY_TITLES.get(clan.family_id, _title_from_id(clan.family_id))


def _public_clan_summary(clan: GeneratedClan) -> str:
    if clan.description and not _looks_technical(clan.description):
        return clan.description
    if clan.family_id in _FAMILY_SUMMARIES:
        return _FAMILY_SUMMARIES[clan.family_id]
    return "A documented monster group observed in the current region. Details are still being filled in by scouts."


def _public_clan_visual(clan: GeneratedClan) -> dict[str, object]:
    visual = clan.flavor_content.get("visual")
    if isinstance(visual, dict):
        return dict(visual)
    return get_family_visual(clan.family_id)


def _public_member_visual(member: GeneratedMonster) -> dict[str, object]:
    visual = member.generation_meta.get("visual")
    if isinstance(visual, dict):
        return dict(visual)
    family_id = member.family_id
    return get_family_visual(family_id) if family_id else {}


def _public_habitat(clan: GeneratedClan) -> str:
    tags = _tags_from_raw(clan.raw_tags)
    labels = [_TAG_LABELS[tag] for tag in tags if tag in _TAG_LABELS and tag not in {"mid", "low", "high"}]
    if labels:
        return ", ".join(labels)
    if clan.zone_id:
        return "charted ruins"
    return "unknown territory"


def _public_location_key(clan: GeneratedClan) -> str:
    biome_id = clan.raw_tags.get("biome_id") or clan.raw_tags.get("biome")
    if biome_id:
        return str(biome_id)
    return "unknown"


def _public_danger(tier: int) -> str:
    if tier <= 1:
        return "Low threat"
    if tier <= 3:
        return "Rising threat"
    if tier <= 5:
        return "High threat"
    return "Extreme threat"


def _public_danger_key(tier: int) -> str:
    if tier <= 1:
        return "low"
    if tier <= 3:
        return "rising"
    if tier <= 5:
        return "high"
    return "extreme"


def _public_filter_tags(clan: GeneratedClan) -> list[dict[str, str]]:
    location_key = _public_location_key(clan)
    result: list[dict[str, str]] = []
    for tag in _tags_from_raw(clan.raw_tags):
        if tag in {location_key, "low", "mid", "high"}:
            continue
        result.append({"key": tag, "label": _TAG_LABELS.get(tag, _title_from_id(tag))})
    return sorted(result, key=lambda item: item["label"])


def _public_member_danger(threat_rating: int) -> str:
    if threat_rating < 50:
        return "Minor threat"
    if threat_rating < 150:
        return "Serious threat"
    if threat_rating < 600:
        return "Deadly threat"
    return "Boss threat"


def _public_member_description(member: GeneratedMonster) -> str:
    if member.description and not _looks_technical(member.description):
        return member.description
    return "A recorded form from this group. Field notes are still incomplete."


def _public_stats(stats: dict[str, int]) -> list[dict[str, object]]:
    return [
        {"label": _STAT_LABELS.get(key, _title_from_id(key)), "value": value}
        for key, value in sorted(stats.items())
        if isinstance(value, int)
    ]


def _public_skills(skills: dict[str, object]) -> list[str]:
    labels = []
    for skill_id, value in skills.items():
        if not value:
            continue
        label = _title_from_id(skill_id)
        labels.append(label.removeprefix("Skill "))
    return labels


def _public_loadout(items: dict[str, object]) -> list[dict[str, str]]:
    layout = items.get("layout") if isinstance(items, dict) else {}
    equipment = layout.get("equipment") if isinstance(layout, dict) else {}
    by_id = items.get("by_id") if isinstance(items, dict) else {}
    return [
        {
            "slot": _LOADOUT_LABELS.get(str(slot), _title_from_id(str(slot))),
            "item": _title_from_id(str((by_id.get(str(item_id)) or {}).get("base_id") or item_id)),
        }
        for slot, item_id in (equipment if isinstance(equipment, dict) else {}).items()
        if item_id
    ]


def _clean_generated_title(value: str) -> str:
    title = value.strip()
    for suffix in (" T0", " T1", " T2", " T3", " T4", " T5", " T6", " T7"):
        if title.endswith(suffix):
            return title[: -len(suffix)]
    return title


def _looks_technical(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in (" adapted to ", " under ", "_", " t0", " t1", " t2", " t3"))

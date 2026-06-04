from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.backend.config.settings import settings
from src.backend.features.generation_ai.image_prompt_contract import NO_TEXT_IMAGE_CONTRACT

DEFAULT_IMAGE_MODEL = settings.gemini_monster_image_model
CLAN_STYLE_VERSION = 3
MEMBER_STYLE_VERSION = 4
GENERATED_MONSTER_STORAGE_ROOT = "monsters/generated"
GENERATED_ASSET_URL_MARKER = "/static/generated-assets/"


@dataclass(frozen=True, slots=True)
class MonsterFamilyVisual:
    family_id: str
    image_url: str
    prompt_seed: str
    member_prompt_seed: str
    clan_subject_contract: str


FAMILY_VISUALS: dict[str, MonsterFamilyVisual] = {
    "bandit_gang": MonsterFamilyVisual(
        family_id="bandit_gang",
        image_url="/static/images/monsters/families/bandit_gang.svg",
        prompt_seed=(
            "A gritty fantasy bandit clan from ruined city outskirts, patched leather armor, scavenged blades, "
            "watchful ambushers, full-body group portrait, dark tactical RPG bestiary art."
        ),
        member_prompt_seed=(
            "One gritty fantasy bandit from ruined city outskirts, patched leather armor, scavenged weapons, "
            "watchful ambusher silhouette, full-body tactical RPG character concept art."
        ),
        clan_subject_contract=(
            "Human outlaw bandits only. Keep faces and body proportions human. Do not render goblins, pointed goblin ears, "
            "or non-human raiders."
        ),
    ),
    "goblin_tribe": MonsterFamilyVisual(
        family_id="goblin_tribe",
        image_url="/static/images/monsters/families/goblin_tribe.svg",
        prompt_seed=(
            "A wiry goblin tribe from a collapsed workshop district, scrap tools, stolen trinkets, sharp silhouettes, "
            "full-body group portrait, dark tactical RPG bestiary art."
        ),
        member_prompt_seed=(
            "One wiry goblin from a collapsed workshop district, scrap tools, stolen trinkets, sharp silhouette, "
            "full-body tactical RPG creature concept art."
        ),
        clan_subject_contract=(
            "Goblins only: short wiry goblinoids with pointed ears and inhuman faces. Do not render human bandit leaders, "
            "human outlaws, or mixed human crews."
        ),
    ),
    "rat_swarm": MonsterFamilyVisual(
        family_id="rat_swarm",
        image_url="/static/images/monsters/families/rat_swarm.svg",
        prompt_seed=(
            "A diseased rat swarm from flooded old-city drains, ragged fur, pale eyes, cellar shadows, "
            "creeping mass composition, dark tactical RPG bestiary art."
        ),
        member_prompt_seed=(
            "One diseased mutant rat creature from flooded old-city drains, ragged fur, pale eyes, cellar shadows, "
            "full-body tactical RPG creature concept art."
        ),
        clan_subject_contract=(
            "Rat creatures only: diseased mutant rats and ratlike monsters. Do not render wolves, humans, goblins, "
            "or humanoid commanders."
        ),
    ),
    "wolf_pack": MonsterFamilyVisual(
        family_id="wolf_pack",
        image_url="/static/images/monsters/families/wolf_pack.svg",
        prompt_seed=(
            "A lean wolf pack from ash-covered city outskirts, scarred hides, alert hunting posture, "
            "full-body group portrait, dark tactical RPG bestiary art."
        ),
        member_prompt_seed=(
            "One lean ash-wolf creature from ash-covered city outskirts, scarred hide, alert hunting posture, "
            "full-body tactical RPG creature concept art."
        ),
        clan_subject_contract=(
            "Wolf creatures only: lean ash-wolves with canine anatomy. Do not render rats, humans, goblins, "
            "or humanoid handlers."
        ),
    ),
}


def get_family_visual(family_id: str) -> dict[str, object]:
    visual = FAMILY_VISUALS.get(family_id)
    if visual is None:
        payload = _visual_asset_payload(
            scope="monster_family_base",
            family_id=family_id,
            prompt_seed="",
            prompt_context={},
        )
        asset_hash = compute_visual_asset_hash(payload)
        return {
            "status": "missing",
            "source": "none",
            "image_url": "",
            "placeholder_image_url": "",
            "generated_image_url": _generated_image_url("families", asset_hash),
            "storage_key": _storage_key("families", asset_hash),
            "asset_hash": asset_hash,
            "storage_backend": settings.asset_storage_backend,
            "image_model": DEFAULT_IMAGE_MODEL,
            "style_version": CLAN_STYLE_VERSION,
            "prompt_seed": "",
            "asset_payload": payload,
        }
    payload = _visual_asset_payload(
        scope="monster_family_base",
        family_id=family_id,
        prompt_seed=visual.prompt_seed,
        prompt_context={},
    )
    asset_hash = compute_visual_asset_hash(payload)
    return {
        "status": "placeholder",
        "source": "family_default",
        "image_url": visual.image_url,
        "placeholder_image_url": visual.image_url,
        "generated_image_url": _generated_image_url("families", asset_hash),
        "storage_key": _storage_key("families", asset_hash),
        "asset_hash": asset_hash,
        "storage_backend": settings.asset_storage_backend,
        "image_model": DEFAULT_IMAGE_MODEL,
        "style_version": CLAN_STYLE_VERSION,
        "prompt_seed": visual.prompt_seed,
        "asset_payload": payload,
    }


def build_clan_visual(
    family_id: str,
    *,
    clan_name: str,
    description: str,
    context_tags: list[str],
    member_roster: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    visual = get_family_visual(family_id)
    visual["scope"] = "monster_clan"
    family_visual = FAMILY_VISUALS.get(family_id)
    prompt_context = {
        "clan_name": clan_name,
        "description": description,
        "context_tags": sorted(set(context_tags)),
        "member_roster": list(member_roster or []),
    }
    payload = _visual_asset_payload(
        scope="monster_clan",
        family_id=family_id,
        prompt_seed=str(visual["prompt_seed"]),
        prompt_context=prompt_context,
        subject_contract=family_visual.clan_subject_contract if family_visual is not None else "",
        style_version=CLAN_STYLE_VERSION,
    )
    asset_hash = compute_visual_asset_hash(payload)
    visual["generated_image_url"] = _generated_image_url("clans", asset_hash)
    visual["storage_key"] = _storage_key("clans", asset_hash)
    visual["asset_hash"] = asset_hash
    visual["asset_payload"] = payload
    visual["prompt_context"] = prompt_context
    return visual


def build_member_visual(
    family_id: str,
    *,
    variant_key: str,
    role: str,
    member_name: str,
    appearance: str,
    visual_hint: str = "",
    context_tags: list[str] | None = None,
    clan_name: str = "",
) -> dict[str, object]:
    visual = get_family_visual(family_id)
    visual["scope"] = "monster_member_template"
    family_visual = FAMILY_VISUALS.get(family_id)
    prompt_seed = family_visual.member_prompt_seed if family_visual is not None else str(visual["prompt_seed"])
    prompt_context = {
        "variant_key": variant_key,
        "role": role,
        "member_name": member_name,
        "appearance": appearance,
        "visual_hint": visual_hint,
        "context_tags": sorted(set(context_tags or [])),
        "clan_name": clan_name,
    }
    payload = _visual_asset_payload(
        scope="monster_member_template",
        family_id=family_id,
        prompt_seed=prompt_seed,
        prompt_context=prompt_context,
        subject_contract="",
        style_version=MEMBER_STYLE_VERSION,
    )
    asset_hash = compute_visual_asset_hash(payload)
    visual["generated_image_url"] = _generated_image_url("members", asset_hash)
    visual["storage_key"] = _storage_key("members", asset_hash)
    visual["asset_hash"] = asset_hash
    visual["asset_payload"] = payload
    visual["prompt_context"] = prompt_context
    visual["prompt_seed"] = prompt_seed
    visual["style_version"] = MEMBER_STYLE_VERSION
    return visual


def build_monster_visual_prompt(asset_payload: dict[str, Any]) -> str:
    prompt_seed = str(asset_payload.get("prompt_seed") or "")
    prompt_context = dict(asset_payload.get("prompt_context") or {})
    scope = str(asset_payload.get("scope") or "monster_visual")
    family_id = str(asset_payload.get("family_id") or "unknown_family")
    subject_contract = str(asset_payload.get("subject_contract") or "")

    lines = [
        "Create a dark fantasy tactical RPG bestiary image.",
        f"Scope: {scope}.",
        f"Base visual direction: {prompt_seed}",
        f"Specific generated context: {json.dumps(prompt_context, ensure_ascii=False, sort_keys=True)}",
        "Style: painterly high-detail creature concept art, grounded materials.",
        NO_TEXT_IMAGE_CONTRACT,
    ]
    if scope == "monster_member_template":
        lines.extend(
            [
                "Internal family identifiers are taxonomy only; do not visualize plural or group meaning from IDs.",
                "Subject contract: render exactly one individual creature or humanoid monster.",
                "Do not render a pack, swarm, gang, band, tribe, group, crowd, companions, minions, duplicate creatures, or background creatures.",
                "Composition: isolated full-body character concept art, one subject only, neutral background.",
            ]
        )
    else:
        lines.insert(2, f"Monster family taxonomy: {family_id}.")
        if subject_contract:
            lines.append(f"Subject contract: {subject_contract}")
        lines.extend(
            [
                "Clan image contract: this is a visual roster reference for this exact clan.",
                "Use the member_roster entries as the canonical subjects; every visible member must match the same species/family and role silhouettes.",
                "Do not mix unrelated species, do not add a different leader species, and do not invent extra faction types outside the roster.",
                "Composition: readable full-body group roster portrait, game-ready key art, neutral background.",
            ]
        )
    return "\n".join(lines)


def compute_visual_asset_hash(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:24]


def version_generated_asset_url(url: str | None, visual: dict[str, Any] | None = None) -> str | None:
    if not url or GENERATED_ASSET_URL_MARKER not in url:
        return url
    version = _visual_cache_version(url, visual or {})
    if not version:
        return url
    return _with_query_param(url, "v", version)


def version_visual_image_urls(visual: dict[str, Any]) -> dict[str, Any]:
    versioned = dict(visual)
    for key in ("image_url", "generated_image_url", "placeholder_image_url", "previous_image_url"):
        value = versioned.get(key)
        if isinstance(value, str) and value:
            versioned[key] = version_generated_asset_url(value, versioned)
    return versioned


def _visual_cache_version(url: str, visual: dict[str, Any]) -> str:
    if url == visual.get("previous_image_url"):
        previous_hash = str(visual.get("previous_asset_hash") or "")
        if previous_hash:
            return previous_hash
    for key in ("asset_hash", "content_hash", "image_hash"):
        value = str(visual.get(key) or "")
        if value:
            return value
    size_bytes = visual.get("size_bytes")
    if size_bytes:
        return f"size-{size_bytes}"
    return ""


def _with_query_param(url: str, key: str, value: str) -> str:
    parts = urlsplit(url)
    query = [(name, item) for name, item in parse_qsl(parts.query, keep_blank_values=True) if name != key]
    query.append((key, value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _visual_asset_payload(
    *,
    scope: str,
    family_id: str,
    prompt_seed: str,
    prompt_context: dict[str, Any],
    subject_contract: str = "",
    style_version: int = CLAN_STYLE_VERSION,
) -> dict[str, Any]:
    return {
        "scope": scope,
        "model": DEFAULT_IMAGE_MODEL,
        "style_version": style_version,
        "family_id": family_id,
        "prompt_seed": prompt_seed,
        "prompt_context": prompt_context,
        "subject_contract": subject_contract,
    }


def _storage_key(scope_dir: str, asset_hash: str) -> str:
    return f"{GENERATED_MONSTER_STORAGE_ROOT}/{scope_dir}/{asset_hash}.webp"


def _generated_image_url(scope_dir: str, asset_hash: str) -> str:
    base_url = settings.asset_public_base_url.rstrip("/")
    return f"{base_url}/{_storage_key(scope_dir, asset_hash)}"

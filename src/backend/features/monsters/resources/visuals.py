from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from src.backend.config.settings import settings

DEFAULT_IMAGE_MODEL = "nano-banana-gemini-2.5-flash-preview-image"
STYLE_VERSION = 1
GENERATED_MONSTER_STORAGE_ROOT = "monsters/generated"


@dataclass(frozen=True, slots=True)
class MonsterFamilyVisual:
    family_id: str
    image_url: str
    prompt_seed: str


FAMILY_VISUALS: dict[str, MonsterFamilyVisual] = {
    "bandit_gang": MonsterFamilyVisual(
        family_id="bandit_gang",
        image_url="/static/images/monsters/families/bandit_gang.svg",
        prompt_seed=(
            "A gritty fantasy bandit clan from ruined city outskirts, patched leather armor, scavenged blades, "
            "watchful ambushers, full-body group portrait, dark tactical RPG bestiary art."
        ),
    ),
    "goblin_tribe": MonsterFamilyVisual(
        family_id="goblin_tribe",
        image_url="/static/images/monsters/families/goblin_tribe.svg",
        prompt_seed=(
            "A wiry goblin tribe from a collapsed workshop district, scrap tools, stolen trinkets, sharp silhouettes, "
            "full-body group portrait, dark tactical RPG bestiary art."
        ),
    ),
    "rat_swarm": MonsterFamilyVisual(
        family_id="rat_swarm",
        image_url="/static/images/monsters/families/rat_swarm.svg",
        prompt_seed=(
            "A diseased rat swarm from flooded old-city drains, ragged fur, pale eyes, cellar shadows, "
            "creeping mass composition, dark tactical RPG bestiary art."
        ),
    ),
    "wolf_pack": MonsterFamilyVisual(
        family_id="wolf_pack",
        image_url="/static/images/monsters/families/wolf_pack.svg",
        prompt_seed=(
            "A lean wolf pack from ash-covered city outskirts, scarred hides, alert hunting posture, "
            "full-body group portrait, dark tactical RPG bestiary art."
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
            "fallback_image_url": "",
            "generated_image_url": _generated_image_url("families", asset_hash),
            "storage_key": _storage_key("families", asset_hash),
            "asset_hash": asset_hash,
            "storage_backend": settings.asset_storage_backend,
            "image_model": DEFAULT_IMAGE_MODEL,
            "style_version": STYLE_VERSION,
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
        "status": "fallback",
        "source": "family_default",
        "image_url": visual.image_url,
        "fallback_image_url": visual.image_url,
        "generated_image_url": _generated_image_url("families", asset_hash),
        "storage_key": _storage_key("families", asset_hash),
        "asset_hash": asset_hash,
        "storage_backend": settings.asset_storage_backend,
        "image_model": DEFAULT_IMAGE_MODEL,
        "style_version": STYLE_VERSION,
        "prompt_seed": visual.prompt_seed,
        "asset_payload": payload,
    }


def build_clan_visual(family_id: str, *, clan_name: str, description: str, context_tags: list[str]) -> dict[str, object]:
    visual = get_family_visual(family_id)
    visual["scope"] = "monster_clan"
    prompt_context = {
        "clan_name": clan_name,
        "description": description,
        "context_tags": sorted(set(context_tags)),
    }
    payload = _visual_asset_payload(
        scope="monster_clan",
        family_id=family_id,
        prompt_seed=str(visual["prompt_seed"]),
        prompt_context=prompt_context,
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
) -> dict[str, object]:
    visual = get_family_visual(family_id)
    visual["scope"] = "monster_member_template"
    prompt_context = {
        "variant_key": variant_key,
        "role": role,
        "member_name": member_name,
        "appearance": appearance,
    }
    payload = _visual_asset_payload(
        scope="monster_member_template",
        family_id=family_id,
        prompt_seed=str(visual["prompt_seed"]),
        prompt_context=prompt_context,
    )
    asset_hash = compute_visual_asset_hash(payload)
    visual["generated_image_url"] = _generated_image_url("members", asset_hash)
    visual["storage_key"] = _storage_key("members", asset_hash)
    visual["asset_hash"] = asset_hash
    visual["asset_payload"] = payload
    visual["prompt_context"] = prompt_context
    return visual


def build_monster_visual_prompt(asset_payload: dict[str, Any]) -> str:
    prompt_seed = str(asset_payload.get("prompt_seed") or "")
    prompt_context = dict(asset_payload.get("prompt_context") or {})
    scope = str(asset_payload.get("scope") or "monster_visual")
    family_id = str(asset_payload.get("family_id") or "unknown_family")

    return "\n".join(
        [
            "Create a dark fantasy tactical RPG bestiary image.",
            f"Scope: {scope}.",
            f"Monster family: {family_id}.",
            f"Base visual direction: {prompt_seed}",
            f"Specific generated context: {json.dumps(prompt_context, ensure_ascii=False, sort_keys=True)}",
            "Style: painterly high-detail creature concept art, grounded materials, no UI, no text, no watermark.",
            "Composition: readable full-body or group portrait, game-ready key art, neutral background.",
        ]
    )


def compute_visual_asset_hash(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:24]


def _visual_asset_payload(
    *,
    scope: str,
    family_id: str,
    prompt_seed: str,
    prompt_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "scope": scope,
        "model": DEFAULT_IMAGE_MODEL,
        "style_version": STYLE_VERSION,
        "family_id": family_id,
        "prompt_seed": prompt_seed,
        "prompt_context": prompt_context,
    }


def _storage_key(scope_dir: str, asset_hash: str) -> str:
    return f"{GENERATED_MONSTER_STORAGE_ROOT}/{scope_dir}/{asset_hash}.webp"


def _generated_image_url(scope_dir: str, asset_hash: str) -> str:
    base_url = settings.asset_public_base_url.rstrip("/")
    return f"{base_url}/{_storage_key(scope_dir, asset_hash)}"

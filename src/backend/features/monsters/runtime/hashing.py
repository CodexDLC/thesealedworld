from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from src.backend.features.monsters.resources.spawn_config import CONTEXT_HASH_TAGS_WHITELIST


@dataclass(frozen=True, slots=True)
class MonsterHashContext:
    source: Literal["world", "rift", "scenario"]
    context_key: str
    biome_id: str
    tier: int
    tags: tuple[str, ...] = ()


def normalize_tags(raw_tags: Iterable[str] | Mapping[str, Any] | None) -> list[str]:
    if raw_tags is None:
        return []
    if isinstance(raw_tags, Mapping):
        tags = [str(key) for key, value in raw_tags.items() if bool(value)]
    else:
        tags = [str(tag) for tag in raw_tags]
    return sorted(set(tags) & CONTEXT_HASH_TAGS_WHITELIST)


def compute_context_hash(tier: int, biome_id: str, normalized_tags: Iterable[str]) -> str:
    tags_key = "_".join(sorted(normalized_tags))
    raw_key = f"{biome_id}:t{tier}:{tags_key}"
    return hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()


def normalized_monster_hash_tags(context: MonsterHashContext) -> list[str]:
    if context.source == "world":
        return normalize_tags(context.tags)
    return _normalize_unfiltered_tags(context.tags)


def compute_monster_context_hash(context: MonsterHashContext) -> str:
    normalized_tags = normalized_monster_hash_tags(context)
    if context.source == "world":
        return compute_context_hash(context.tier, context.biome_id, normalized_tags)
    if context.source == "rift":
        return compute_rift_context_hash(
            setting_key=context.context_key,
            tier=context.tier,
            biome_id=context.biome_id,
            tags=normalized_tags,
        )
    tags_key = "_".join(normalized_tags)
    raw_key = (
        f"{context.source}:{context.context_key}:{context.biome_id}:t{max(1, min(7, int(context.tier)))}:{tags_key}"
    )
    return hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()


def compute_rift_context_hash(
    *,
    setting_key: str,
    tier: int,
    biome_id: str,
    tags: Iterable[str] | Mapping[str, Any] | None = None,
) -> str:
    normalized_tags = _normalize_rift_tags(tags)
    tags_key = "_".join(normalized_tags)
    raw_key = f"rift:{setting_key}:{biome_id}:t{max(1, min(7, int(tier)))}:{tags_key}"
    return hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()


def compute_unique_clan_hash(family_id: str, context_hash: str) -> str:
    raw_key = f"{family_id}:{context_hash}"
    return hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()


def _normalize_rift_tags(raw_tags: Iterable[str] | Mapping[str, Any] | None) -> list[str]:
    return _normalize_unfiltered_tags(raw_tags)


def _normalize_unfiltered_tags(raw_tags: Iterable[str] | Mapping[str, Any] | None) -> list[str]:
    if raw_tags is None:
        return []
    if isinstance(raw_tags, Mapping):
        tags = [str(key).strip() for key, value in raw_tags.items() if bool(value)]
    else:
        tags = [str(tag).strip() for tag in raw_tags]
    return sorted({tag for tag in tags if tag})

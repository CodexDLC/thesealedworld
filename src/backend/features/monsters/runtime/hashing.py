from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import Any

from src.backend.features.monsters.resources.spawn_config import CONTEXT_HASH_TAGS_WHITELIST


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


def compute_unique_clan_hash(family_id: str, context_hash: str) -> str:
    raw_key = f"{family_id}:{context_hash}"
    return hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()

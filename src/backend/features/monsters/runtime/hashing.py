from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class MonsterHashContext:
    source: Literal["world", "rift", "scenario"]
    context_key: str
    biome_id: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MonsterHabitatIdentity:
    biome: str
    keys: tuple[str, ...] = ()


def normalize_habitat_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def normalize_habitat_keys(raw_keys: Iterable[str] | Mapping[str, Any] | None) -> list[str]:
    if raw_keys is None:
        return []
    if isinstance(raw_keys, Mapping):
        values = [str(key) for key, enabled in raw_keys.items() if bool(enabled)]
    else:
        values = [str(key) for key in raw_keys]
    return sorted({key for key in (normalize_habitat_token(value) for value in values) if key})


def normalize_habitat(*, biome: str, keys: Iterable[str] | Mapping[str, Any] | None = None) -> MonsterHabitatIdentity:
    return MonsterHabitatIdentity(
        biome=normalize_habitat_token(biome) or "wasteland",
        keys=tuple(normalize_habitat_keys(keys)),
    )


def compute_habitat_hash(*, biome: str, keys: Iterable[str] | Mapping[str, Any] | None = None) -> str:
    habitat = normalize_habitat(biome=biome, keys=keys)
    return _digest("habitat_v1", habitat.biome, ",".join(habitat.keys))


def compute_clan_identity_hash(
    *,
    family_id: str,
    biome: str,
    keys: Iterable[str] | Mapping[str, Any] | None = None,
    selected_trait_keys: Iterable[str] | None = None,
    generation_version: int = 2,
    resource_version: float | str = 1.0,
    seed_namespace: str = "habitat_clan_identity_v1",
) -> str:
    habitat = normalize_habitat(biome=biome, keys=keys)
    traits = sorted({normalize_habitat_token(key) for key in selected_trait_keys or [] if normalize_habitat_token(key)})
    return _digest(
        seed_namespace,
        normalize_habitat_token(family_id),
        habitat.biome,
        ",".join(habitat.keys),
        ",".join(traits),
        str(int(generation_version)),
        str(resource_version),
    )


def normalize_tags(raw_tags: Iterable[str] | Mapping[str, Any] | None) -> list[str]:
    return normalize_habitat_keys(raw_tags)


def compute_context_hash(tier: int, biome_id: str, normalized_tags: Iterable[str]) -> str:
    del tier
    tags_key = "_".join(sorted(normalized_tags))
    raw_key = f"{biome_id}:{tags_key}"
    return hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()


def normalized_monster_hash_tags(context: MonsterHashContext) -> list[str]:
    if context.source == "world":
        return normalize_tags(context.tags)
    return _normalize_unfiltered_tags(context.tags)


def compute_monster_context_hash(context: MonsterHashContext) -> str:
    normalized_tags = normalized_monster_hash_tags(context)
    if context.source == "world":
        return compute_context_hash(0, context.biome_id, normalized_tags)
    if context.source == "rift":
        return compute_rift_context_hash(
            setting_key=context.context_key,
            tier=0,
            biome_id=context.biome_id,
            tags=normalized_tags,
        )
    tags_key = "_".join(normalized_tags)
    raw_key = f"{context.source}:{context.context_key}:{context.biome_id}:{tags_key}"
    return hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()


def compute_rift_context_hash(
    *,
    setting_key: str,
    tier: int,
    biome_id: str,
    tags: Iterable[str] | Mapping[str, Any] | None = None,
) -> str:
    del tier
    normalized_tags = _normalize_rift_tags(tags)
    tags_key = "_".join(normalized_tags)
    raw_key = f"rift:{setting_key}:{biome_id}:{tags_key}"
    return hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()


def compute_unique_clan_hash(
    family_id: str,
    context_hash: str,
    *,
    generation_version: int = 1,
    resource_version: float | str = 1.0,
    seed_namespace: str = "clan_identity_v1",
) -> str:
    return _digest(
        seed_namespace, str(family_id), str(context_hash), str(int(generation_version)), str(resource_version)
    )


def _normalize_rift_tags(raw_tags: Iterable[str] | Mapping[str, Any] | None) -> list[str]:
    return _normalize_unfiltered_tags(raw_tags)


def _normalize_unfiltered_tags(raw_tags: Iterable[str] | Mapping[str, Any] | None) -> list[str]:
    return normalize_habitat_keys(raw_tags)


def _digest(*parts: str) -> str:
    raw_key = ":".join(str(part) for part in parts)
    return hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()

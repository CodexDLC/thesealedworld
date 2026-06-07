from __future__ import annotations

from typing import Any

from src.backend.features.monsters.resources.visuals import version_generated_asset_url, version_visual_image_urls


class MonsterCombatActorInputBuilder:
    """Builds combat-facing actor input from a generated monster tier snapshot."""

    def build_input(self, monster: Any) -> dict[str, Any]:
        snapshot = dict(getattr(monster, "active_snapshot", None) or {})
        combat_input = snapshot.get("combat_snapshot_input")
        if not isinstance(combat_input, dict):
            raise ValueError(
                f"Generated monster is missing combat_snapshot_input: {getattr(monster, 'id', '<unknown>')}"
            )
        return dict(combat_input)

    def build_snapshot(self, monster: Any) -> dict[str, Any]:
        actor_input = self.build_input(monster)
        meta = dict(actor_input.get("meta") or {})
        source = dict(actor_input.get("source") or {})
        visual = _monster_visual(monster)
        if visual:
            source["visual"] = version_visual_image_urls(visual)
        avatar_url = _monster_avatar_url(visual)
        if avatar_url:
            meta["avatar_url"] = avatar_url
        return {
            "meta": meta,
            "source": source,
            "status": dict(actor_input.get("status") or {}),
            "combat": {
                "math_model": dict(actor_input.get("raw") or {}),
                "skills": dict(actor_input.get("skills") or {}),
                "loadout": dict(actor_input.get("loadout") or {}),
            },
        }


def _monster_visual(monster: Any) -> dict[str, Any]:
    actor_document = getattr(monster, "actor_document", None)
    if not isinstance(actor_document, dict):
        return {}
    base_projection = actor_document.get("base_projection")
    if not isinstance(base_projection, dict):
        return {}
    visual = base_projection.get("visual")
    if not isinstance(visual, dict):
        return {}
    return dict(visual)


def _monster_avatar_url(visual: dict[str, Any]) -> str | None:
    for key in ("image_url", "generated_image_url", "placeholder_image_url"):
        value = visual.get(key)
        if value:
            return version_generated_asset_url(str(value), visual)
    return None


__all__ = ["MonsterCombatActorInputBuilder"]

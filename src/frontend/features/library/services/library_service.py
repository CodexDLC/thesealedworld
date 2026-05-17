from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from src.frontend.integrations.backend_api.game_catalog import BackendGameCatalogApi


class LibraryFrontendService:
    def __init__(self, *, catalog_api: BackendGameCatalogApi) -> None:
        self.catalog_api = catalog_api

    async def monster_clans(
        self,
        *,
        tier: str | None = None,
        location: str | None = None,
        family: str | None = None,
        tag: str | None = None,
        danger: str | None = None,
        sort: str = "tier_title",
        view: str = "cards",
        q: str | None = None,
    ) -> dict:
        clans = await self._generated_monster_clans()
        options = _build_filter_options(clans)
        selected = {
            "tier": _clean_choice(tier),
            "location": _clean_choice(location),
            "family": _clean_choice(family),
            "tag": _clean_choice(tag),
            "danger": _clean_choice(danger),
            "sort": sort if sort in _SORT_LABELS else "tier_title",
            "view": view if view in {"cards", "list"} else "cards",
            "q": (q or "").strip(),
        }
        filtered = _sort_clans(_filter_clans(clans, selected), selected["sort"])
        return {
            "clans": filtered,
            "options": options,
            "selected": selected,
            "sort_options": [{"key": key, "label": label} for key, label in _SORT_LABELS.items()],
            "total_count": len(clans),
            "filtered_count": len(filtered),
            "view": selected["view"],
        }

    async def monster_clan_detail(self, clan_id: str) -> dict | None:
        clans = await self._generated_monster_clans()
        return next((clan for clan in clans if str(clan.get("id")) == clan_id), None)

    async def _generated_monster_clans(self) -> list[dict]:
        try:
            return await self.catalog_api.get_public_generated_monster_clans()
        except Exception:
            logger.opt(exception=True).warning("Generated monster clan catalog unavailable")
            return []


_SORT_LABELS = {
    "tier_title": "Тир, название",
    "title": "Название",
    "forms_desc": "Больше форм",
    "forms_asc": "Меньше форм",
}


def _clean_choice(value: str | None) -> str:
    if value is None or value == "all":
        return "all"
    return value


def _filter_clans(clans: list[dict], selected: dict[str, str]) -> list[dict]:
    result = clans
    if selected["tier"] != "all":
        result = [clan for clan in result if str(clan.get("tier")) == selected["tier"]]
    if selected["location"] != "all":
        result = [clan for clan in result if str(clan.get("location_key")) == selected["location"]]
    if selected["family"] != "all":
        result = [clan for clan in result if str(clan.get("family_key")) == selected["family"]]
    if selected["danger"] != "all":
        result = [clan for clan in result if str(clan.get("danger_key")) == selected["danger"]]
    if selected["tag"] != "all":
        result = [
            clan
            for clan in result
            if selected["tag"]
            in {str(item.get("key")) for item in clan.get("filter_tags", []) if isinstance(item, dict)}
        ]
    if selected["q"]:
        needle = selected["q"].lower()
        result = [clan for clan in result if needle in _search_text(clan)]
    return result


def _sort_clans(clans: list[dict], sort: str) -> list[dict]:
    if sort == "title":
        return sorted(clans, key=lambda clan: str(clan.get("title", "")))
    if sort == "forms_desc":
        return sorted(clans, key=lambda clan: (-int(clan.get("member_count") or 0), str(clan.get("title", ""))))
    if sort == "forms_asc":
        return sorted(clans, key=lambda clan: (int(clan.get("member_count") or 0), str(clan.get("title", ""))))
    return sorted(clans, key=lambda clan: (int(clan.get("tier") or 0), str(clan.get("title", ""))))


def _build_filter_options(clans: list[dict]) -> dict[str, list[dict[str, str]]]:
    tiers = sorted({int(clan.get("tier") or 0) for clan in clans})
    locations = {
        str(clan.get("location_key")): str(
            clan.get("location_label") or clan.get("habitat") or clan.get("location_key")
        )
        for clan in clans
        if clan.get("location_key")
    }
    families = {
        str(clan.get("family_key")): str(clan.get("family_label") or clan.get("title") or clan.get("family_key"))
        for clan in clans
        if clan.get("family_key")
    }
    dangers = {
        str(clan.get("danger_key")): str(clan.get("danger"))
        for clan in clans
        if clan.get("danger_key") and clan.get("danger")
    }
    tags: dict[str, str] = {}
    for clan in clans:
        for item in clan.get("filter_tags", []):
            if isinstance(item, dict) and item.get("key"):
                tags[str(item["key"])] = str(item.get("label") or item["key"])

    return {
        "tiers": [{"key": str(tier), "label": f"Тир {tier}"} for tier in tiers],
        "locations": [{"key": key, "label": locations[key]} for key in sorted(locations, key=lambda k: locations[k])],
        "families": [{"key": key, "label": families[key]} for key in sorted(families, key=lambda k: families[k])],
        "dangers": [{"key": key, "label": dangers[key]} for key in sorted(dangers, key=lambda k: dangers[k])],
        "tags": [{"key": key, "label": tags[key]} for key in sorted(tags, key=lambda k: tags[k])],
    }


def _search_text(clan: dict) -> str:
    tags = " ".join(str(item.get("label", "")) for item in clan.get("filter_tags", []) if isinstance(item, dict))
    return " ".join(
        [
            str(clan.get("title", "")),
            str(clan.get("summary", "")),
            str(clan.get("habitat", "")),
            tags,
        ]
    ).lower()

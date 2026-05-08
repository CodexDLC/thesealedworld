from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

from src.backend.features.game_catalog.combat.resources.abilities import get_all_abilities
from src.backend.features.game_catalog.combat.resources.effects import get_all_effects
from src.backend.features.game_catalog.combat.resources.feints import get_all_feint_catalog_entries
from src.backend.features.game_catalog.combat.resources.gifts import get_all_gifts
from src.backend.features.game_catalog.combat.resources.tokens import get_all_combat_tokens
from src.backend.features.game_catalog.combat.resources.triggers import get_all_triggers

if TYPE_CHECKING:
    from pydantic import BaseModel


@dataclass(slots=True)
class CombatResourceCatalogService:
    """Read-only projections of combat resources for runtime lookups and UI text."""

    @classmethod
    def load_default(cls) -> CombatResourceCatalogService:
        return cls()

    def all_public_text(self) -> dict[str, dict[str, dict[str, Any]]]:
        combat_entries = self._catalog_entries_by_key(get_all_feint_catalog_entries())
        return {
            "abilities": self._catalog_by_id(get_all_abilities(), id_field="ability_id"),
            "feints": self._catalog_entries_by_id(get_all_feint_catalog_entries(), id_field="feint_id"),
            "effects": self._catalog_by_id(get_all_effects(), id_field="effect_id"),
            "triggers": self._catalog_by_id(get_all_triggers(), id_field="id"),
            "gifts": self._catalog_by_id(get_all_gifts(), id_field="gift_id"),
            "combat_tokens": self._public_mapping(get_all_combat_tokens()),
            "combat_entries": combat_entries,
        }

    @staticmethod
    def _public_mapping(entries: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {str(entry_id): dict(data) for entry_id, data in entries.items()}

    def _catalog_by_id(self, entries: Sequence[BaseModel], *, id_field: str) -> dict[str, dict[str, Any]]:
        catalog: dict[str, dict[str, Any]] = {}
        for entry in entries:
            data = entry.model_dump(mode="json")
            entry_id = str(data[id_field])
            catalog[entry_id] = self._public_entry(entry_id, data)
        return catalog

    def _catalog_entries_by_id(self, entries: Sequence[BaseModel], *, id_field: str) -> dict[str, dict[str, Any]]:
        catalog: dict[str, dict[str, Any]] = {}
        for entry in entries:
            data = entry.model_dump(mode="json")
            technical = data["technical"]
            descriptive = data["descriptive"]
            entry_id = str(technical[id_field])
            public = self._public_entry_from_description(entry_id, descriptive)
            for field in ("cost", "target", "target_count"):
                if field in technical and technical[field] not in (None, [], {}):
                    public[field] = technical[field]
            public["catalog_key"] = data["key"]
            catalog[entry_id] = public
        return catalog

    def _catalog_entries_by_key(self, entries: Sequence[BaseModel]) -> dict[str, dict[str, Any]]:
        catalog: dict[str, dict[str, Any]] = {}
        for entry in entries:
            data = entry.model_dump(mode="json")
            key = str(data["key"])
            technical = data["technical"]
            descriptive = data["descriptive"]
            public = self._public_entry_from_description(key, descriptive)
            public["catalog_key"] = key
            public["resource_type"] = key.split(".")[1] if "." in key else ""
            public["resource_id"] = technical.get("feint_id") or key
            if technical.get("cost") not in (None, [], {}):
                public["cost"] = technical["cost"]
            catalog[key] = public
        return catalog

    @staticmethod
    def _public_entry(entry_id: str, data: dict[str, Any]) -> dict[str, Any]:
        title = data.get("name_ru") or data.get("name_en") or entry_id
        description = (
            data.get("description_ru") or data.get("description") or f"DATA_MISSING: combat_description:{entry_id}"
        )
        public: dict[str, Any] = {
            "title": title,
            "description": description,
        }
        for field in (
            "source",
            "type",
            "target",
            "target_count",
            "event",
            "chance",
            "school",
            "role",
            "duration",
            "tags",
        ):
            if field in data and data[field] not in (None, [], {}):
                public[field] = data[field]
        return public

    @staticmethod
    def _public_entry_from_description(entry_id: str, descriptive: dict[str, Any]) -> dict[str, Any]:
        default_taxonomy = descriptive.get("default_taxonomy") or "humanoid"
        variants = descriptive.get("variants") or {}
        selected = variants.get(default_taxonomy) or variants.get("humanoid") or {}
        return {
            "title": selected.get("display_name") or entry_id,
            "label": selected.get("ui_label") or selected.get("display_name") or entry_id,
            "description": selected.get("short_description") or f"DATA_MISSING: combat_description:{entry_id}",
            "long_description": selected.get("long_description") or selected.get("short_description") or "",
            "icon": selected.get("icon") or "",
            "default_taxonomy": default_taxonomy,
            "taxonomy_variants": variants,
        }

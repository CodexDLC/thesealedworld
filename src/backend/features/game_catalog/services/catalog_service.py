from __future__ import annotations

import hashlib
import json

from src.backend.features.character.resources import CHARACTER_ATTRIBUTE_TEXT
from src.backend.features.game_catalog.combat.resources import CombatResourceCatalogService
from src.backend.features.game_catalog.dto import GameCatalogBootstrapDTO, GameCatalogManifestDTO
from src.backend.features.game_catalog.skills.services import SkillCatalogService
from src.backend.features.items.services import ItemCatalogService


class GameCatalogBootstrapService:
    VERSION = "game-catalog:2026-05-03.1"

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

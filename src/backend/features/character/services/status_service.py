from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from src.backend.features.game_catalog.skills.dto import SkillGroup
from src.backend.features.game_catalog.skills.services import SkillCatalogService
from src.shared.schemas.character import CharacterStatusDTO
from src.shared.schemas.character_status import CharacterActorCoreDTO
from src.shared.schemas.panel import PanelDTO, PanelWidgetDTO

if TYPE_CHECKING:
    from src.backend.features.character.integrations import CharacterStateIntegrator
    from src.backend.features_site.auth.models import User


ATTRIBUTE_GROUPS = [
    {
        "title": "BODY",
        "items": [
            ("strength", "СИЛ"),
            ("agility", "ЛОВ"),
            ("endurance", "ВЫН"),
        ],
    },
    {
        "title": "CORE",
        "items": [
            ("intellect", "ИНТ"),
            ("memory", "ПАМ"),
            ("mental", "МЕН"),
        ],
    },
    {
        "title": "SENSOR",
        "items": [
            ("perception", "ВОС"),
            ("projection", "ПРО"),
            ("prediction", "ПРД"),
        ],
    },
]

SKILL_GROUP_ORDER = [
    SkillGroup.WEAPON_MASTERY.value,
    SkillGroup.TACTICAL.value,
    SkillGroup.ARMOR.value,
    SkillGroup.COMBAT_SUPPORT.value,
    SkillGroup.GATHERING.value,
    SkillGroup.CRAFTING.value,
    SkillGroup.TRADE.value,
    SkillGroup.SOCIAL.value,
    SkillGroup.SURVIVAL.value,
    SkillGroup.SCIENCE.value,
    SkillGroup.OTHER.value,
]

SKILL_GROUP_TITLES = {
    SkillGroup.WEAPON_MASTERY.value: "WEAPON MASTERY",
    SkillGroup.TACTICAL.value: "TACTICAL",
    SkillGroup.ARMOR.value: "ARMOR",
    SkillGroup.COMBAT_SUPPORT.value: "COMBAT SUPPORT",
    SkillGroup.GATHERING.value: "GATHERING",
    SkillGroup.CRAFTING.value: "CRAFTING",
    SkillGroup.TRADE.value: "TRADE",
    SkillGroup.SOCIAL.value: "SOCIAL",
    SkillGroup.SURVIVAL.value: "SURVIVAL",
    SkillGroup.SCIENCE.value: "SCIENCE",
    SkillGroup.OTHER.value: "OTHER",
}


class CharacterStatusService:
    def __init__(
        self,
        *,
        state_integrator: CharacterStateIntegrator,
        skill_catalog: SkillCatalogService | None = None,
    ) -> None:
        self.state_integrator = state_integrator
        self.skill_catalog = skill_catalog or SkillCatalogService()

    async def get_actor_core(
        self,
        user: User,
        char_id: int,
    ) -> CharacterActorCoreDTO:
        active = await self.state_integrator.get_actor_core(user.id, char_id)

        return CharacterActorCoreDTO.model_validate(
            {
                "key": active.key,
                **active.document,
                "panel": self._build_panel(active.document),
            }
        )

    async def get_status(
        self,
        user: User,
        char_id: int,
    ) -> CharacterStatusDTO:
        return self._format_status(await self.state_integrator.get_status_document(user.id, char_id))

    @staticmethod
    def _format_status(doc: dict[str, Any]) -> CharacterStatusDTO:
        bio = doc.get("bio") or {}
        vitals = doc.get("vitals") or {}
        hp = vitals.get("hp") or {}
        energy = vitals.get("energy") or {}
        stamina = vitals.get("stamina") or {}
        return CharacterStatusDTO(
            character_id=int(doc.get("char_id", 0)),
            name=str(bio.get("name", "")),
            avatar_url=bio.get("avatar"),
            hp=float(hp.get("cur", 0)),
            max_hp=int(hp.get("max", 1)),
            energy=float(energy.get("cur", 0)),
            max_energy=int(energy.get("max", 1)),
            stamina=float(stamina.get("cur", 0)),
            max_stamina=int(stamina.get("max", 1)),
            last_update=datetime.fromtimestamp(float(vitals.get("last_update", 0.0)), UTC),
        )

    def _build_panel(self, document: dict) -> PanelDTO:
        bio = document.get("bio") or {}
        vitals = document.get("vitals") or {}
        attributes = document.get("attributes") or {}
        skills = document.get("skills") or {}
        resources = document.get("resources") or document.get("wallet") or {}

        return PanelDTO(
            id="character_status",
            title="STATUS",
            widgets=[
                PanelWidgetDTO(
                    type="avatar",
                    title="PROFILE",
                    data={
                        "name": bio.get("name", "AGENT"),
                        "avatar": bio.get("avatar"),
                        "state": document.get("state", "UNKNOWN"),
                        "resources": self._resource_items(resources),
                    },
                ),
                PanelWidgetDTO(
                    type="vitals",
                    title="VITALS",
                    items=[
                        self._vital_item("HP", vitals.get("hp"), "hp"),
                        self._vital_item("EN", vitals.get("energy"), "en"),
                        self._vital_item("STAMINA", vitals.get("stamina"), "sta"),
                    ],
                ),
                PanelWidgetDTO(
                    type="attribute_grid",
                    title="ATTRIBUTES",
                    data={"groups": self._attribute_groups(attributes)},
                ),
                PanelWidgetDTO(
                    type="skill_groups",
                    title="SKILLS",
                    data={"groups": self._skill_groups(skills)},
                ),
            ],
        )

    @staticmethod
    def _vital_item(label: str, value: dict | None, variant: str) -> dict:
        value = value or {}
        return {
            "label": label,
            "cur": value.get("cur", 0),
            "max": value.get("max", 1),
            "variant": variant,
        }

    @staticmethod
    def _resource_items(resources: dict) -> list[dict]:
        if not resources:
            return []
        return [
            {"label": key.upper(), "icon": key[:2].upper(), "value": value}
            for key, value in resources.items()
            if isinstance(value, int | float | str)
        ]

    @staticmethod
    def _attribute_groups(attributes: dict) -> list[dict]:
        groups: list[dict] = []
        for group in ATTRIBUTE_GROUPS:
            items = []
            for key, short_label in group["items"]:
                value = attributes.get(key)
                if isinstance(value, int | float):
                    items.append(
                        {
                            "label": short_label,
                            "value": value,
                            "catalog": "attributes",
                            "catalog_key": key,
                        }
                    )
            groups.append({"title": group["title"], "items": items})
        return groups

    def _skill_groups(self, skills: dict) -> list[dict]:
        groups: dict[str, dict] = {}
        for key, value in skills.items():
            skill_key = str(key)
            definition = self.skill_catalog.get(skill_key)
            group_key = definition.group.value if definition else SkillGroup.OTHER.value
            group = groups.setdefault(
                group_key,
                {
                    "key": group_key,
                    "title": SKILL_GROUP_TITLES.get(group_key, group_key.replace("_", " ").upper()),
                    "category": definition.category.value if definition else None,
                    "order": SKILL_GROUP_ORDER.index(group_key)
                    if group_key in SKILL_GROUP_ORDER
                    else len(SKILL_GROUP_ORDER),
                    "items": [],
                },
            )
            group["items"].append(
                {
                    "label": definition.name_ru if definition else skill_key,
                    "value": self._skill_value(value),
                    "catalog": "skills",
                    "catalog_key": skill_key,
                }
            )

        return [
            {key: value for key, value in group.items() if key != "order"}
            for group in sorted(groups.values(), key=lambda item: (item["order"], item["title"]))
        ]

    @staticmethod
    def _skill_value(value: object) -> object:
        if isinstance(value, dict):
            return value.get("xp", value.get("total_xp", value.get("value", 0)))
        return value

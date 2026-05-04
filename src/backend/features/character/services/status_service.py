from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.character.runtime import CharacterVitalsCalculator
from src.backend.features.game_catalog.skills.dto import SkillGroup
from src.backend.features.game_catalog.skills.services import SkillCatalogService
from src.backend.infrastructure.actor_state import CharacterRepository
from src.backend.infrastructure.actor_state.schemas.session import (
    CharacterSessionAttributesDTO,
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionLocationDTO,
    CharacterSessionSymbioteDTO,
    CharacterSessionVitalsDTO,
)
from src.shared.schemas.character import CharacterStatusDTO
from src.shared.schemas.character_status import CharacterActorCoreDTO
from src.shared.schemas.panel import PanelDTO, PanelWidgetDTO

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features_site.auth.models import User
    from src.backend.infrastructure.actor_state.managers.session import CharacterSessionManager
    from src.backend.infrastructure.actor_state.schemas.session import CharacterGender


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
        character_sessions: CharacterSessionManager,
        skill_catalog: SkillCatalogService | None = None,
    ) -> None:
        self.character_sessions = character_sessions
        self.skill_catalog = skill_catalog or SkillCatalogService()

    async def get_actor_core(
        self,
        user: User,
        char_id: int,
        db_session: AsyncSession,
    ) -> CharacterActorCoreDTO:
        repo = CharacterRepository(db_session)
        character = await repo.get_by_id_and_user_id(char_id, user.id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")

        session_doc = await self._get_or_initialize_session_doc(char_id, character)
        document = session_doc.model_dump(mode="json")

        return CharacterActorCoreDTO.model_validate(
            {
                "key": self.character_sessions.build_key(char_id),
                **document,
                "panel": self._build_panel(document),
            }
        )

    async def get_status(
        self,
        user: User,
        char_id: int,
        db_session: AsyncSession,
    ) -> CharacterStatusDTO:
        repo = CharacterRepository(db_session)
        character = await repo.get_by_id_and_user_id(char_id, user.id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")

        session_doc = await self._get_or_initialize_session_doc(char_id, character)

        previous_last_update = session_doc.vitals.last_update
        updated_vitals = self._apply_vitals_regen(session_doc.vitals)
        if updated_vitals.last_update != previous_last_update:
            session_doc.vitals = updated_vitals
            session_doc.updated_at = datetime.now(UTC)
            await self.character_sessions.update_session(char_id, session_doc.model_dump(mode="json"))

        return self._format_status(session_doc)

    async def _get_or_initialize_session_doc(self, char_id: int, character) -> CharacterSessionDocumentDTO:
        document = await self.character_sessions.get_session(char_id)
        if document is None:
            return await self._initialize_session_from_character(character)
        session_doc = CharacterSessionDocumentDTO.model_validate(document)
        repaired_doc, changed = self._repair_session_from_persisted_actor_state(session_doc, character)
        if changed:
            repaired_doc.updated_at = datetime.now(UTC)
            await self.character_sessions.update_session(char_id, repaired_doc.model_dump(mode="json"))
        return repaired_doc

    async def _initialize_session_from_character(self, character) -> CharacterSessionDocumentDTO:
        attributes = self._session_attributes_from_character(character)
        session_doc = CharacterSessionDocumentDTO(
            char_id=character.character_id,
            user_id=character.user_id,
            bio=CharacterSessionBioDTO(
                name=character.name,
                gender=cast("CharacterGender", character.gender),
                avatar=character.avatar_url,
                created_at=character.created_at or datetime.now(UTC),
            ),
            location=CharacterSessionLocationDTO(current=character.location_id or "52_52"),
            vitals=CharacterVitalsCalculator.build_vitals_from_snapshot(
                getattr(character, "vitals_snapshot", None),
                attributes,
            ),
            attributes=attributes,
            skills=self._session_skills_from_character(character),
            symbiote=CharacterSessionSymbioteDTO(
                name=character.symbiote.symbiote_name if character.symbiote else "Symbiote",
                gift_rank=character.symbiote.gift_rank if character.symbiote else 1,
            ),
            updated_at=datetime.now(UTC),
        )
        await self.character_sessions.create_session(character.character_id, session_doc.model_dump(mode="json"))
        return session_doc

    @staticmethod
    def _session_attributes_from_character(character) -> CharacterSessionAttributesDTO:
        attributes = getattr(character, "attributes", None)
        if attributes is None:
            return CharacterSessionAttributesDTO()

        return CharacterSessionAttributesDTO(
            strength=int(getattr(attributes, "strength", 8)),
            agility=int(getattr(attributes, "agility", 8)),
            endurance=int(getattr(attributes, "endurance", 8)),
            intellect=int(getattr(attributes, "intellect", 8)),
            memory=int(getattr(attributes, "memory", 8)),
            mental=int(getattr(attributes, "mental", 8)),
            perception=int(getattr(attributes, "perception", 8)),
            projection=int(getattr(attributes, "projection", 8)),
            prediction=int(getattr(attributes, "prediction", 8)),
        )

    @staticmethod
    def _session_skills_from_character(character) -> dict[str, dict[str, object]]:
        skills = getattr(character, "skill_progress", None) or []
        session_skills: dict[str, dict[str, object]] = {}
        for skill in skills:
            if not getattr(skill, "is_unlocked", False):
                continue
            state = getattr(skill, "progress_state", None)
            session_skills[str(skill.skill_key)] = {
                "xp": float(getattr(skill, "total_xp", 0.0) or 0.0),
                "unlocked": True,
                "state": getattr(state, "value", state) or "PLUS",
            }
        return session_skills

    def _repair_session_from_persisted_actor_state(
        self,
        session_doc: CharacterSessionDocumentDTO,
        character,
    ) -> tuple[CharacterSessionDocumentDTO, bool]:
        changed = False

        persisted_attributes = self._session_attributes_from_character(character)
        if not self._attributes_are_default(persisted_attributes) and self._attributes_are_default(
            session_doc.attributes
        ):
            session_doc.attributes = persisted_attributes
            changed = True

        persisted_skills = self._session_skills_from_character(character)
        if persisted_skills:
            merged_skills = dict(session_doc.skills)
            for skill_key, value in persisted_skills.items():
                if skill_key not in merged_skills:
                    merged_skills[skill_key] = value
                    changed = True
            session_doc.skills = merged_skills

        refreshed_vitals = CharacterVitalsCalculator.refresh_max_vitals(
            session_doc.vitals,
            session_doc.attributes,
            fill_if_default=True,
        )
        if refreshed_vitals != session_doc.vitals:
            session_doc.vitals = refreshed_vitals
            changed = True

        return session_doc, changed

    @staticmethod
    def _attributes_are_default(attributes: CharacterSessionAttributesDTO) -> bool:
        return all(value == 8 for value in attributes.model_dump(mode="json").values())

    @staticmethod
    def _apply_vitals_regen(vitals: CharacterSessionVitalsDTO) -> CharacterSessionVitalsDTO:
        now = datetime.now(UTC).timestamp()
        if vitals.last_update <= 0:
            vitals.last_update = now
            return vitals

        elapsed = now - vitals.last_update
        if elapsed < 1.0:
            return vitals

        for attr_name in ("hp", "energy", "stamina"):
            value = getattr(vitals, attr_name)
            if value.cur < value.max and value.regen > 0:
                value.cur = min(value.max, int(value.cur + value.regen * elapsed))

        vitals.last_update = now
        return vitals

    @staticmethod
    def _format_status(doc: CharacterSessionDocumentDTO) -> CharacterStatusDTO:
        return CharacterStatusDTO(
            character_id=doc.char_id,
            name=doc.bio.name,
            avatar_url=doc.bio.avatar,
            hp=float(doc.vitals.hp.cur),
            max_hp=doc.vitals.hp.max,
            energy=float(doc.vitals.energy.cur),
            max_energy=doc.vitals.energy.max,
            stamina=float(doc.vitals.stamina.cur),
            max_stamina=doc.vitals.stamina.max,
            last_update=datetime.fromtimestamp(doc.vitals.last_update, UTC),
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

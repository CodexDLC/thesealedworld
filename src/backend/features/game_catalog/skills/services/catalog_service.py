from functools import cached_property

from src.backend.features.game_catalog.skills.dto import SkillCategory, SkillDefinitionDTO, SkillGroup
from src.backend.features.game_catalog.skills.resources import build_indexes, load_skill_definitions


class SkillCatalogService:
    @cached_property
    def skills(self) -> list[SkillDefinitionDTO]:
        return load_skill_definitions()

    @cached_property
    def by_key(self) -> dict[str, SkillDefinitionDTO]:
        return {skill.skill_key: skill for skill in self.skills}

    @cached_property
    def by_category(self) -> dict[SkillCategory, list[SkillDefinitionDTO]]:
        by_category, _ = build_indexes(self.skills)
        return by_category

    @cached_property
    def by_group(self) -> dict[SkillGroup, list[SkillDefinitionDTO]]:
        _, by_group = build_indexes(self.skills)
        return by_group

    def get(self, skill_key: str) -> SkillDefinitionDTO | None:
        return self.by_key.get(skill_key)

    def all_public_text(self) -> dict[str, dict[str, object]]:
        return {skill.skill_key: skill.to_public_catalog_item() for skill in self.skills}

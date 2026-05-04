from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup

TRADE_SKILLS = [
    SkillDTO(
        skill_key="accounting",
        name_en="Accounting",
        name_ru="Бухгалтерия",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.TRADE,
        stat_weights={"intellect": 2, "prediction": 2},  # Dual 2+2
        rate_mod=1.0,
        wall_mod=1.0,
        description="Ведение учета и управление финансами.",
    ),
    SkillDTO(
        skill_key="brokerage",
        name_en="Brokerage",
        name_ru="Посредничество",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.TRADE,
        stat_weights={"projection": 2, "prediction": 1, "intellect": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description="Умение договариваться и находить выгодные сделки.",
    ),
    SkillDTO(
        skill_key="contracts",
        name_en="Contracts",
        name_ru="Договоры",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.TRADE,
        stat_weights={"intellect": 2, "projection": 1, "prediction": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description="Составление и заключение юридически грамотных договоров.",
    ),
    SkillDTO(
        skill_key="trade_relations",
        name_en="Trade Relations",
        name_ru="Торговые связи",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.TRADE,
        stat_weights={"projection": 2, "prediction": 2},  # Dual 2+2
        rate_mod=1.0,
        wall_mod=1.0,
        description="Установление и поддержание торговых отношений.",
    ),
]

from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup, SkillUiGroup

TRADE_SKILLS = [
    SkillDTO(
        skill_key="skill_accounting",
        name_en="Accounting",
        name_ru="Бухгалтерия",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        ui_group=SkillUiGroup.TRADE,
        stat_weights={"intellect": 2, "prediction": 2},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Финансовый контроль: учет, комиссии, налоги, обмены и потери на операциях.\n\n"
            "Даёт: снижение торговых комиссий, налогов и потерь при обмене валют. Ограничение: "
            "не создает прибыль сам по себе, а уменьшает издержки."
        ),
    ),
    SkillDTO(
        skill_key="skill_brokerage",
        name_en="Brokerage",
        name_ru="Посредничество",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        ui_group=SkillUiGroup.TRADE,
        stat_weights={"projection": 2, "prediction": 1, "intellect": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Посредничество на рынке: доступ к сделкам, удаленная торговля и работа с ордерами.\n\n"
            "Даёт: больше торговых слотов, расширенный доступ к аукциону и buy orders. Ограничение: "
            "требует рынок, NPC или торговую инфраструктуру."
        ),
    ),
    SkillDTO(
        skill_key="skill_contracts",
        name_en="Contracts",
        name_ru="Договоры",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        ui_group=SkillUiGroup.TRADE,
        stat_weights={"intellect": 2, "projection": 1, "prediction": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Работа с договорами, поручениями, юридическими условиями и лимитами активных обязательств.\n\n"
            "Даёт: больше активных заданий и торговых поручений, надежнее формальные сделки. "
            "Ограничение: влияет на емкость и условия, а не на боевую силу."
        ),
    ),
    SkillDTO(
        skill_key="skill_trade_relations",
        name_en="Trade Relations",
        name_ru="Торговые связи",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        ui_group=SkillUiGroup.TRADE,
        stat_weights={"projection": 2, "prediction": 2},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Репутация и связи с торговцами, фракциями и закрытыми поставщиками.\n\n"
            "Даёт: лучшие цены покупки/продажи, доступ к скрытым товарам и улучшение отношений с NPC. "
            "Ограничение: зависит от фракций и локальной экономики."
        ),
    ),
]

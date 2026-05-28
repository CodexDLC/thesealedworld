from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatDescriptionDTO,
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import pipeline_mutation
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

_DUAL_TAGS = ["tactical", "dual_wield", "skill_dual_wield", "weapon", "melee"]


TACTICAL_DUAL_WIELD_FEINTS_TECHNICAL = {
    "broken_step": FeintTechnicalDTO(
        feint_id="broken_step",
        cost=FeintCostDTO(tactics={"hit": 2, "dodge": 1}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "dodge", "counter"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_broken_step", "target_actor": "source"}],
    ),
    "shifting_line": FeintTechnicalDTO(
        feint_id="shifting_line",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "dodge", "parry_boost"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_shifting_line", "target_actor": "source"}],
    ),
    "empty_line": FeintTechnicalDTO(
        feint_id="empty_line",
        cost=FeintCostDTO(tactics={"hit": 4, "dodge": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "dodge", "damage_reduction"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_empty_line", "target_actor": "source"}],
    ),
    "torn_rhythm": FeintTechnicalDTO(
        feint_id="torn_rhythm",
        cost=FeintCostDTO(tactics={"hit": 5, "dodge": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "dodge", "counter_cap"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_torn_rhythm", "target_actor": "source"}],
    ),
    "bind_blade": FeintTechnicalDTO(
        feint_id="bind_blade",
        cost=FeintCostDTO(tactics={"hit": 2, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "parry", "debuff"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_bind_blade", "target_actor": "source"}],
    ),
    "offhand_over": FeintTechnicalDTO(
        feint_id="offhand_over",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "parry", "counter"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_offhand_over", "target_actor": "source"}],
    ),
    "open_vein": FeintTechnicalDTO(
        feint_id="open_vein",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "parry", "crit_chance"],
        purchase_group="tactical",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.30,
                tags=["dual_wield", "dagger_window"],
            )
        ],
    ),
    "silent_puncture": FeintTechnicalDTO(
        feint_id="silent_puncture",
        cost=FeintCostDTO(tactics={"hit": 5, "parry": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "parry", "forced_crit", "weapon_trigger", "damage"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("force.crit"),
            pipeline_mutation("crit_damage_boost"),
        ],
    ),
    "answering_series": FeintTechnicalDTO(
        feint_id="answering_series",
        cost=FeintCostDTO(tactics={"hit": 3, "counter": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "counter", "damage"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_answering_series_counter", "target_actor": "source"}],
    ),
    "blade_mill": FeintTechnicalDTO(
        feint_id="blade_mill",
        cost=FeintCostDTO(tactics={"hit": 5, "counter": 4}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "counter", "damage", "offhand", "high_cost"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_blade_mill_counter", "target_actor": "source"}],
    ),
    "blade_loop": FeintTechnicalDTO(
        feint_id="blade_loop",
        cost=FeintCostDTO(tactics={"hit": 6, "parry": 3, "counter": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "parry", "counter", "debuff", "high_cost", "requires_dual_075"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_blade_loop_parry", "target_actor": "source"}],
    ),
}

_DUAL_TEXTS = {
    "broken_step": (
        "Ломаный шаг",
        "Усилить контру с уворота",
        "Дуальный финт: следующий успешный уворот повышает шанс контратаки.",
        "ломая линию шага",
        "и оставляет окно для ответа",
        "и превращает уход в опасный ответ",
    ),
    "shifting_line": (
        "Смена линии",
        "Поднять парирование",
        "Дуальный финт: следующая входящая атака проходит против усиленного парирования.",
        "перенося вторую руку на встречную линию",
        "и усиливает парирование",
        "и закрывает клинок второй рукой",
    ),
    "empty_line": (
        "Пустая линия",
        "Срезать входящий урон",
        "Дуальный финт: следующий входящий удар наносит половину урона.",
        "оставляя перед собой пустую линию",
        "и принимает удар вскользь",
        "и уводит силу атаки в сторону",
    ),
    "torn_rhythm": (
        "Рваный ритм",
        "Контра от капа",
        "Дуальный финт: следующий успешный уворот проверяет контратаку от капа.",
        "сбивая ритм двумя клинками",
        "и ищет предельное окно контратаки",
        "и ловит высокий темп ответа",
    ),
    "bind_blade": (
        "Связать клинок",
        "Сбить урон с парирования",
        "Дуальный финт: следующее успешное парирование снижает следующий исходящий урон атакующего.",
        "готовя связку клинка",
        "и связывает оружие противника",
        "и сбивает силу следующего удара",
    ),
    "offhand_over": (
        "Вторая рука сверху",
        "Открыть контру с парирования",
        "Дуальный финт: следующее успешное парирование открывает контратаку и повышает ее шанс.",
        "поднимая вторую руку над линией",
        "и переводит парирование в ответ",
        "и открывает встречную серию",
    ),
    "open_vein": (
        "Открытая жила",
        "Поднять шанс крита",
        "Дуальный финт: следующий удар получает повышенный шанс крита.",
        "выискивая тонкую линию",
        "и открывает шанс критического прокола",
        "и находит живую точку",
    ),
    "silent_puncture": (
        "Тихий прокол",
        "Гарантировать крит",
        "Дуальный финт: следующий удар критический и наносит усиленный критический урон.",
        "пряча второй клинок",
        "и проводит тихий критический прокол",
        "и раскрывает броню точным проколом",
    ),
    "answering_series": (
        "Ответная серия",
        "Усилить контратаку",
        "Дуальный финт: следующая успешная контратака наносит больше урона.",
        "собирая ответную серию",
        "и усиливает встречную атаку",
        "и вкладывает темп в ответ",
    ),
    "blade_mill": (
        "Мельница двух рук",
        "Усилить контру и offhand",
        "Дуальный финт: следующая успешная контратака наносит больше урона и запускает удар второй рукой.",
        "заводя клинки в мельницу",
        "и переводит контратаку во вторую руку",
        "и раскручивает два клинка в ответ",
    ),
    "blade_loop": (
        "Петля клинков",
        "Парировать в сильную контру",
        "Дуальный финт: следующее парирование вызывает усиленную контратаку и снижает следующий урон цели.",
        "замыкая клинки в петлю",
        "и ловит атаку в петлю",
        "и затягивает противника в ответную связку",
    ),
}


def _dual_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _DUAL_TEXTS[feint_id]
    return build_combat_description(
        resource_type="feints",
        resource_id=feint_id,
        icon=f"combat/feints/{feint_id}.svg",
        display_name=display_name,
        ui_label=ui_label,
        short_description=short,
        humanoid_long_description=short,
        humanoid_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но дуальная линия не находит цели"],
            dodge=["но {target} уходит из-под связки"],
            parry=["но {target} сбивает связку"],
            block=["но {target} гасит серию защитой"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но дуальная линия не находит цели"],
            dodge=["но {target} уходит из-под связки"],
            parry=["но {target} сбивает движение"],
            block=["но серия гаснет о защиту {target}"],
        ),
    )


TACTICAL_DUAL_WIELD_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_dual_description(feint_id),
    )
    for feint_id, technical in TACTICAL_DUAL_WIELD_FEINTS_TECHNICAL.items()
}

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatDescriptionDTO,
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

_DUAL_TAGS = ["tactical", "dual_wield", "skill_dual_wield", "melee"]


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
        applicability_tags=[*_DUAL_TAGS, "hit", "parry", "debuff", "blade_lock"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_bind_blade", "target_actor": "source"}],
    ),
    "offhand_over": FeintTechnicalDTO(
        feint_id="offhand_over",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "parry", "counter", "blade_lock"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_offhand_over", "target_actor": "source"}],
    ),
    "answering_series": FeintTechnicalDTO(
        feint_id="answering_series",
        cost=FeintCostDTO(tactics={"hit": 3, "pressure": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "pressure", "counter", "damage"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_answering_series_counter", "target_actor": "source"}],
    ),
    "blade_loop": FeintTechnicalDTO(
        feint_id="blade_loop",
        cost=FeintCostDTO(tactics={"hit": 6, "parry": 3, "pressure": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[
            *_DUAL_TAGS,
            "hit",
            "parry",
            "pressure",
            "counter",
            "debuff",
            "high_cost",
            "blade_lock",
            "requires_dual_075",
        ],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_blade_loop_parry", "target_actor": "source"}],
    ),
    "dual_blade_mill_v2": FeintTechnicalDTO(
        feint_id="dual_blade_mill_v2",
        cost=FeintCostDTO(tactics={"hit": 5, "pressure": 4}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "pressure", "counter", "damage", "high_cost"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_blade_mill_counter", "target_actor": "source"}],
    ),
    "dual_split_targets": FeintTechnicalDTO(
        feint_id="dual_split_targets",
        cost=FeintCostDTO(tactics={"hit": 2, "dodge": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "dodge", "coordination", "multi_focus"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_split_targets", "target_actor": "source"}],
    ),
    "dual_chain_follow": FeintTechnicalDTO(
        feint_id="dual_chain_follow",
        cost=FeintCostDTO(tactics={"hit": 2, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "parry", "coordination", "offhand_boost"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_chain_follow", "target_actor": "source"}],
    ),
    "dual_paired_open": FeintTechnicalDTO(
        feint_id="dual_paired_open",
        cost=FeintCostDTO(tactics={"hit": 2, "pressure": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "pressure", "coordination", "crit_window"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_paired_open", "target_actor": "source"}],
    ),
    "dual_cross_lock": FeintTechnicalDTO(
        feint_id="dual_cross_lock",
        cost=FeintCostDTO(tactics={"hit": 2, "parry": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "parry", "blade_lock", "forced_parry", "debuff"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_cross_lock", "target_actor": "source"}],
    ),
    "dual_blade_vise": FeintTechnicalDTO(
        feint_id="dual_blade_vise",
        cost=FeintCostDTO(tactics={"hit": 2, "parry": 4}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "hit", "parry", "blade_lock", "counter", "control", "anti_archer"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_dual_blade_vise", "target_actor": "source"}],
    ),
    "dual_crimson_lock": FeintTechnicalDTO(
        feint_id="dual_crimson_lock",
        cost=FeintCostDTO(tactics={"blood": 2, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_TAGS, "blood", "parry", "blade_lock", "reflect", "counter"],
        purchase_group="tactical",
        preparation_effects=[
            {
                "id": "prep_dual_crimson_lock",
                "target_actor": "source",
                "params": {"reflect_ratio": 0.50},
            }
        ],
    ),
}

_DUAL_TEXTS = {
    "broken_step": (
        "Ломаный шаг",
        "ломая линию шага усилить ответ с уворота",
        "Дуальный финт: следующий успешный уворот повышает шанс контратаки.",
        "ломая линию шага",
        "и оставляет окно для ответа",
        "и превращает уход в опасный ответ",
    ),
    "shifting_line": (
        "Смена линии",
        "перенося вторую руку на встречную линию поднять парирование",
        "Дуальный финт: следующая входящая атака проходит против усиленного парирования.",
        "перенося вторую руку на встречную линию",
        "и усиливает парирование",
        "и закрывает клинок второй рукой",
    ),
    "empty_line": (
        "Пустая линия",
        "оставив перед собой пустую линию срезать входящий урон",
        "Дуальный финт: следующий входящий удар наносит половину урона.",
        "оставляя перед собой пустую линию",
        "и принимает удар вскользь",
        "и уводит силу атаки в сторону",
    ),
    "torn_rhythm": (
        "Рваный ритм",
        "сбивая ритм найти контратаку от капа",
        "Дуальный финт: следующий успешный уворот проверяет контратаку от капа.",
        "сбивая ритм двумя клинками",
        "и ищет предельное окно контратаки",
        "и ловит высокий темп ответа",
    ),
    "bind_blade": (
        "Связать клинок",
        "связав клинок противника сбить его следующий урон",
        "Дуальный финт-замок: следующее успешное парирование связывает оружие цели и режет её следующий урон.",
        "сводя клинки в замок вокруг оружия противника",
        "и связывает оружие противника",
        "и сбивает силу следующего удара",
    ),
    "offhand_over": (
        "Вторая рука сверху",
        "подняв вторую руку перевести парирование в ответ",
        "Дуальный финт-замок: следующее успешное парирование открывает контратаку и повышает её шанс.",
        "поднимая вторую руку над линией",
        "и переводит парирование в ответ",
        "и открывает встречную серию",
    ),
    "answering_series": (
        "Ответная серия",
        "собирая ответную серию усилить контратаку",
        "Дуальный финт: следующая успешная контратака наносит больше урона.",
        "собирая ответную серию",
        "и усиливает встречную атаку",
        "и вкладывает темп в ответ",
    ),
    "blade_loop": (
        "Петля клинков",
        "замыкая клинки в петлю поймать парирование и сбить урон цели",
        "Дуальный финт-замок: следующее парирование вызывает усиленную контратаку и снижает следующий урон цели.",
        "замыкая клинки в петлю",
        "и ловит атаку в петлю",
        "и затягивает противника в ответную связку",
    ),
    "dual_blade_mill_v2": (
        "Мельница двух рук",
        "заводя клинки в мельницу обрушить обе руки на контратаке",
        "Дуальный финт: следующая успешная контратака наносит больше урона и обеими руками.",
        "заводя клинки в мельницу",
        "и переводит контратаку во вторую руку",
        "и раскручивает два клинка в ответ",
    ),
    "dual_split_targets": (
        "Раздвоенная линия",
        "разводя клинки атаковать две линии",
        "Дуальный финт-координация: в следующем размене основная рука бьет основную цель, вторая — соседнюю.",
        "разводя клинки по двум линиям",
        "и собирает удар сразу по двум линиям",
        "и пересекает строй сразу двумя клинками",
    ),
    "dual_chain_follow": (
        "Связка по ритму",
        "поймав ритм продолжить второй рукой",
        "Дуальный финт-координация: если основная рука попала в следующем размене, вторая рука получает прибавку к урону.",
        "ловя ритм основной руки",
        "и продолжает связку второй рукой",
        "и точно ловит вторую руку в окно",
    ),
    "dual_paired_open": (
        "Парное окно",
        "подняв шанс крита раскрыть окно для обеих рук",
        "Дуальный финт-координация: если основная рука крит в следующем размене, вторая рука получает прибавку к шансу крита.",
        "поднимая шанс крита для обеих рук",
        "и раскрывает критовое окно для второй руки",
        "и собирает обеими руками критовое окно",
    ),
    "dual_cross_lock": (
        "Крестовой замок",
        "сводя клинки в замок поймать оружие противника",
        "Дуальный финт-замок: следующая входящая атака гарантированно парируется и оставляет цель раскрытой.",
        "сводя клинки в крестовой замок",
        "и ловит оружие противника между лезвиями",
        "и затягивает оружие цели в замок",
    ),
    "dual_blade_vise": (
        "Тиски клинков",
        "стиснув клинки сорвать темп противника",
        "Дуальный финт-замок: следующее парирование вызывает контратаку и срывает концентрацию цели, лучника принуждает к ближнему бою.",
        "стискивая клинки вокруг оружия противника",
        "и срывает темп цели парированием в замке",
        "и стискивает противника в опасные тиски",
    ),
    "dual_crimson_lock": (
        "Алый замок",
        "впитав удар свести клинки в замок ответа",
        "Дуальный финт-замок: следующее парирование возвращает 50% урона цели.",
        "оставляя кровь на линии замка",
        "и возвращает удар через замок клинков",
        "и превращает замок в болезненный ответ",
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

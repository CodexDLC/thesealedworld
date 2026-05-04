"""
РУКОВОДСТВО ПО ЗАПОЛНЕНИЮ: ОРУЖИЕ И ЩИТЫ
=========================================

Этот файл содержит шаблоны для оружия и щитов.

КЛАССИФИКАЦИЯ ПО СЛОТАМ:
--------------------------
- slot: Основной слот ('main_hand', 'two_hand', 'off_hand').
- extra_slots: Список доп. слотов. Например, для кинжала:
    - slot: 'main_hand'
    - extra_slots: ['off_hand']
  Это позволит носить его в любой руке.

КЛЮЧЕВЫЕ ПОЛЯ:
---------------
- base_power: Средний урон (для оружия) или показатель защиты (для щитов).
- damage_spread: Разброс урона в % (0.1 = +/- 10%).
- implicit_bonuses: Врожденные бонусы (точность, крит, парирование).
- related_skill: Навык, отвечающий за владение этим предметом (XP, бонусы, штрафы).
"""

from src.backend.features.items.resources.schemas import BaseItemDTO

WEAPONS_DB = {
    # ==========================================
    # 1. ЛЕГКОЕ ОДНОРУЧНОЕ (Main Hand / Off Hand)
    # Skill: light_weapons
    # ==========================================
    "light_1h": {
        "dagger": BaseItemDTO(
            id="dagger",
            name_ru="Кинжал",
            narrative_description="Короткий клинок для быстрых ударов, скрытого ношения и точного добивания вблизи.",
            slot="main_hand",
            extra_slots=["off_hand"],
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=3,
            damage_spread=0.05,
            base_durability=40,
            narrative_tags=["dagger", "swift", "stealth"],
            implicit_bonuses={
                "physical_crit_chance": 0.15,
                "physical_pierce_chance": 0.15,
                "physical_accuracy": 0.10,
            },
            triggers=["crit.bleed_on_crit"],  # NEW ID
        ),
        "knife": BaseItemDTO(
            id="knife",
            name_ru="Нож",
            narrative_description="Простой рабочий клинок, больше похожий на инструмент, но достаточно острый для драки.",
            slot="main_hand",
            extra_slots=["off_hand"],
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=2,
            damage_spread=0.1,
            base_durability=35,
            narrative_tags=["knife", "tool", "simple"],
            implicit_bonuses={
                "physical_crit_chance": 0.05,
            },
            triggers=["crit.bleed_on_crit"],  # NEW ID
        ),
        "tanto": BaseItemDTO(
            id="tanto",
            name_ru="Танто",
            narrative_description="Короткий прямой клинок с жесткой геометрией, рассчитанный на быстрый укол и чистый разрез.",
            slot="main_hand",
            extra_slots=["off_hand"],
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=4,
            damage_spread=0.05,
            base_durability=45,
            narrative_tags=["tanto", "samurai", "short"],
            implicit_bonuses={
                "physical_crit_chance": 0.10,
                "physical_pierce_chance": 0.10,
            },
            triggers=["crit.bleed_on_crit"],  # NEW ID
        ),
        "hatchet": BaseItemDTO(
            id="hatchet",
            name_ru="Топорик",
            narrative_description="Легкий рубящий топор, удобный в тесном бою и грубой полевой работе.",
            slot="main_hand",
            extra_slots=["off_hand"],
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=4,
            damage_spread=0.3,
            base_durability=50,
            narrative_tags=["axe", "light", "chop"],
            implicit_bonuses={
                "physical_crit_power_float": 0.50,
                "bleed_damage_bonus": 0.15,
            },
            triggers=["crit.heavy_strike_on_crit"],  # NEW ID
        ),
        "wakizashi": BaseItemDTO(
            id="wakizashi",
            name_ru="Вакидзаси",
            narrative_description="Короткая изогнутая сабля, сохраняющая баланс между быстрым ударом и уверенным парированием.",
            slot="main_hand",
            extra_slots=["off_hand"],
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=4,
            damage_spread=0.1,
            base_durability=55,
            narrative_tags=["wakizashi", "samurai", "blade"],
            implicit_bonuses={
                "physical_accuracy": 0.15,
                "parry_chance": 0.10,
                "counter_attack_chance": 0.05,
            },
            triggers=["crit.bleed_on_crit"],  # NEW ID
        ),
    },
    # ==========================================
    # 2. СРЕДНЕЕ ОДНОРУЧНОЕ (Main Hand Only)
    # Skill: medium_weapons
    # ==========================================
    "medium_1h": {
        "sword": BaseItemDTO(
            id="sword",
            name_ru="Меч",
            narrative_description="Сбалансированное одноручное оружие для рубящих и колющих ударов без явных слабостей.",
            slot="main_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=5,
            damage_spread=0.1,
            base_durability=60,
            narrative_tags=["sword", "balanced", "blade"],
            implicit_bonuses={
                "physical_accuracy": 0.10,
                "parry_chance": 0.10,
            },
            triggers=["crit.bleed_on_crit"],  # NEW ID
        ),
        "shortsword": BaseItemDTO(
            id="shortsword",
            name_ru="Короткий меч",
            narrative_description="Компактный меч для ближней дистанции, быстрых выпадов и боя в узких проходах.",
            slot="main_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=4,
            damage_spread=0.1,
            base_durability=55,
            narrative_tags=["sword", "short", "agile"],
            implicit_bonuses={
                "physical_accuracy": 0.10,
                "attack_speed": 0.05,
            },
            triggers=["crit.bleed_on_crit"],  # NEW ID
        ),
        "scimitar": BaseItemDTO(
            id="scimitar",
            name_ru="Скимитар",
            narrative_description="Изогнутый клинок, созданный для широких рубящих дуг и кровоточащих порезов.",
            slot="main_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=6,
            damage_spread=0.1,
            base_durability=60,
            narrative_tags=["scimitar", "curved", "slash"],
            implicit_bonuses={
                "bleed_chance": 0.10,
                "parry_chance": 0.05,
            },
            triggers=["crit.bleed_on_crit"],  # NEW ID
        ),
        "longsword": BaseItemDTO(
            id="longsword",
            name_ru="Длинный меч",
            narrative_description="Длинный одноручный клинок с уверенной дистанцией, подходящий для строевого и дуэльного боя.",
            slot="main_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=7,
            damage_spread=0.1,
            base_durability=65,
            narrative_tags=["sword", "long", "knight"],
            implicit_bonuses={
                "parry_chance": 0.10,
                "physical_damage_bonus": 0.05,
            },
            triggers=["crit.bleed_on_crit"],  # NEW ID
        ),
        "battle_axe": BaseItemDTO(
            id="battle_axe",
            name_ru="Боевой топор",
            narrative_description="Тяжелое рубящее оружие с агрессивным балансом, созданное раскалывать защиту одним сильным ударом.",
            slot="main_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=6,
            damage_spread=0.4,
            base_durability=50,
            narrative_tags=["axe", "brutal", "chop"],
            implicit_bonuses={
                "physical_crit_power_float": 0.60,
                "physical_damage_bonus": 0.05,
            },
            triggers=["crit.heavy_strike_on_crit"],  # NEW ID
        ),
        "mace": BaseItemDTO(
            id="mace",
            name_ru="Булава",
            narrative_description="Дробящее оружие с тяжелой головкой, эффективное против брони и костей.",
            slot="main_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=6,
            damage_spread=0.2,
            base_durability=80,
            narrative_tags=["mace", "crushing", "blunt"],
            implicit_bonuses={
                "physical_penetration": 0.25,
                "shock_resistance": 0.10,
            },
            triggers=["crit.stun_on_crit"],  # NEW ID
        ),
        "rapier": BaseItemDTO(
            id="rapier",
            name_ru="Рапира",
            narrative_description="Тонкий колющий клинок для точных выпадов, контроля дистанции и поиска слабых мест.",
            slot="main_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=4,
            damage_spread=0.05,
            base_durability=45,
            narrative_tags=["rapier", "fencing", "piercing"],
            implicit_bonuses={
                "physical_accuracy": 0.20,
                "physical_pierce_chance": 0.10,
                "parry_chance": 0.05,
            },
            triggers=["crit.piercing_crit"],  # NEW ID
        ),
    },
    # ==========================================
    # 3. ДВУРУЧНОЕ ОРУЖИЕ (Two Hand)
    # Skill: heavy_weapons
    # ==========================================
    "melee_2h": {
        "greatsword": BaseItemDTO(
            id="greatsword",
            name_ru="Клеймор",
            narrative_description="Массивный двуручный меч, требующий размаха и силы, но рассекающий широкую зону перед владельцем.",
            slot="two_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=10,
            damage_spread=0.15,
            base_durability=70,
            narrative_tags=["greatsword", "massive", "cleave"],
            implicit_bonuses={
                "parry_chance": 0.15,
                "physical_damage_bonus": 0.15,
            },
            triggers=["crit.bleed_on_crit"],  # NEW ID
        ),
        "warhammer": BaseItemDTO(
            id="warhammer",
            name_ru="Боевой Молот",
            narrative_description="Двуручный молот, переносящий силу удара в сокрушительный импульс против брони и щитов.",
            slot="two_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=12,
            damage_spread=0.3,
            base_durability=90,
            narrative_tags=["hammer", "smash", "heavy"],
            implicit_bonuses={
                "physical_penetration": 0.40,
                "dodge_chance": -0.10,
            },
            triggers=["crit.stun_on_crit"],  # NEW ID
        ),
        "spear": BaseItemDTO(
            id="spear",
            name_ru="Копье",
            narrative_description="Древковое оружие с хорошей дистанцией, позволяющее держать угрозу перед собой.",
            slot="two_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots", "woods"],
            base_power=9,
            damage_spread=0.1,
            base_durability=50,
            narrative_tags=["spear", "reach", "piercing"],
            implicit_bonuses={
                "counter_attack_chance": 0.20,
                "physical_accuracy": 0.10,
                "physical_pierce_chance": 0.05,
            },
            triggers=["crit.piercing_crit"],  # NEW ID
        ),
        "halberd": BaseItemDTO(
            id="halberd",
            name_ru="Алебарда",
            narrative_description="Древковое оружие с лезвием и крюком, совмещающее рубящий удар и контроль позиции.",
            slot="two_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots", "woods"],
            base_power=11,
            damage_spread=0.15,
            base_durability=60,
            narrative_tags=["halberd", "polearm", "chop"],
            implicit_bonuses={
                "physical_penetration": 0.20,
                "counter_attack_chance": 0.15,
            },
            triggers=["crit.heavy_strike_on_crit"],  # NEW ID
        ),
        "katana": BaseItemDTO(
            id="katana",
            name_ru="Катана",
            narrative_description="Изогнутый двуручный клинок, рассчитанный на быстрый чистый разрез и точный ритм боя.",
            slot="two_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["ingots"],
            base_power=9,
            damage_spread=0.1,
            base_durability=65,
            narrative_tags=["katana", "samurai", "fast_blade"],
            implicit_bonuses={
                "physical_crit_chance": 0.15,
                "bleed_damage_bonus": 0.20,
                "physical_accuracy": 0.10,
            },
            triggers=["crit.bleed_on_crit"],  # NEW ID
        ),
        "quarterstaff": BaseItemDTO(
            id="quarterstaff",
            name_ru="Боевой посох",
            narrative_description="Прочный посох для оборонительного боя, перехватов и быстрых ударов с обеих сторон.",
            slot="two_hand",
            type="weapon",
            damage_type="physical",
            defense_type="physical",
            allowed_materials=["woods"],
            base_power=6,
            damage_spread=0.1,
            base_durability=100,
            narrative_tags=["staff", "monk", "defensive"],
            implicit_bonuses={
                "parry_chance": 0.20,
                "dodge_chance": 0.10,
                "counter_attack_chance": 0.10,
            },
            triggers=["crit.stun_on_crit"],  # NEW ID (Added for Staff)
        ),
    },
    # ==========================================
    # 4. ДАЛЬНИЙ БОЙ (Ranged)
    # Skill: archery
    # ==========================================
    "ranged": {
        "sling": BaseItemDTO(
            id="sling",
            name_ru="Праща",
            narrative_description="Простейшее дальнобойное оружие, использующее скорость вращения и камень вместо сложного механизма.",
            slot="main_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["leathers"],
            base_power=4,
            damage_spread=0.2,
            base_durability=30,
            narrative_tags=["sling", "simple", "stone"],
            implicit_bonuses={
                "physical_accuracy": -0.05,
                "physical_crit_power_float": 0.20,
            },
            triggers=["crit.stun_on_crit"],  # NEW ID
        ),
        "shortbow": BaseItemDTO(
            id="shortbow",
            name_ru="Короткий лук",
            narrative_description="Легкий лук для быстрой стрельбы на средней дистанции и маневренного боя.",
            slot="two_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["woods"],
            base_power=6,
            damage_spread=0.1,
            base_durability=40,
            narrative_tags=["bow", "ranger", "fast"],
            implicit_bonuses={
                "physical_accuracy": 0.15,
                "dodge_chance": 0.05,
            },
            triggers=["control.evasive_shot"],  # NEW ID
        ),
        "longbow": BaseItemDTO(
            id="longbow",
            name_ru="Длинный лук",
            narrative_description="Большой лук с сильным натяжением, созданный для дальних точных выстрелов.",
            slot="two_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["woods"],
            base_power=9,
            damage_spread=0.15,
            base_durability=35,
            narrative_tags=["bow", "long_range", "sniper"],
            implicit_bonuses={
                "physical_damage_bonus": 0.15,
                "physical_accuracy": 0.10,
                "physical_pierce_chance": 0.05,
            },
            triggers=["crit.piercing_crit"],  # NEW ID
        ),
        "crossbow": BaseItemDTO(
            id="crossbow",
            name_ru="Арбалет",
            narrative_description="Механическое стрелковое оружие с мощным прямым выстрелом и медленной перезарядкой.",
            slot="two_hand",
            type="weapon",
            damage_type="physical",
            allowed_materials=["woods", "ingots"],
            base_power=12,
            damage_spread=0.05,
            base_durability=60,
            narrative_tags=["crossbow", "heavy", "slow"],
            implicit_bonuses={
                "physical_penetration": 0.40,
                "physical_crit_power_float": 0.50,
            },
            triggers=["crit.unblockable_crit"],  # NEW ID
        ),
    },
    # ==========================================
    # 5. ЩИТЫ (Off Hand Only)
    # Skill: shield_mastery
    # ==========================================
    "shields": {
        "shield": BaseItemDTO(
            id="shield",
            name_ru="Щит",
            narrative_description="Полноразмерный щит для принятия удара, удержания линии и силового давления плечом.",
            slot="off_hand",
            type="armor",
            defense_type="physical",
            allowed_materials=["woods", "ingots"],
            base_power=8,
            base_durability=80,
            damage_spread=0.0,
            narrative_tags=["shield", "block", "protection"],
            implicit_bonuses={
                "shield_block_chance": 0.20,
                "shield_block_power": 0.30,
            },
            triggers=["block.bash_on_block"],  # NEW ID (Added)
        ),
        "buckler": BaseItemDTO(
            id="buckler",
            name_ru="Баклер",
            narrative_description="Небольшой ручной щит для парирования, быстрых сбивов и контратак на близкой дистанции.",
            slot="off_hand",
            type="armor",
            defense_type="physical",
            allowed_materials=["woods", "ingots"],
            base_power=3,
            base_durability=50,
            damage_spread=0.0,
            narrative_tags=["buckler", "parry", "small_shield"],
            implicit_bonuses={
                "parry_chance": 0.15,
                "counter_attack_chance": 0.10,
                "shield_block_chance": 0.05,
            },
            triggers=["parry.counter_on_parry"],  # NEW ID (Added)
        ),
    },
}

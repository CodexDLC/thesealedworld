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

from src.backend.resources.game_data.items.schemas import BaseItemDTO

WEAPONS_DB = {
    # ==========================================
    # 1. ЛЕГКОЕ ОДНОРУЧНОЕ (Main Hand / Off Hand)
    # Skill: light_weapons
    # ==========================================
    "light_1h": {
        "dagger": BaseItemDTO(
            id="dagger",
            name_ru="Кинжал",
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

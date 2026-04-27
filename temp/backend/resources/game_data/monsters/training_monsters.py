from src.backend.resources.game_data.monsters.monster_structs import MonsterLoadout, MonsterStats, MonsterVariant

# Пул тренировочных монстров для туториала.
# БАЛАНС:
# - Гуманоиды: Средние статы, сила в экипировке.
# - Звери: Высокие статы, компенсирующие отсутствие вещей.

TRAINING_POOL: dict[str, MonsterVariant] = {
    # ==================================================
    # ГУМАНОИДЫ (Статы ниже, но есть броня и оружие)
    # ==================================================
    "goblin_spearman_training": {
        "id": "goblin_spearman_training",
        "name_ru": "Гоблин-копейщик",
        "role": "veteran",
        "narrative_hint": "A disciplined goblin with a long spear and a crude wooden shield.",
        "description": "Эти гоблины составляют костяк патрулей в Разломе. Они не блещут умом, но компенсируют это строгой дисциплиной и умением держать строй. Их длинные копья опасны на дистанции.",
        "combat_intro_text": "Гоблин-копейщик поднимает свой грубый щит и выставляет вперед копье, готовясь к атаке.",
        "cost": 50,
        "extra_tags": ["infantry", "shield", "training"],
        "base_stats": MonsterStats(
            strength=10,
            agility=10,
            endurance=11,
            intelligence=5,
            wisdom=5,
            men=6,
            perception=9,
            charisma=5,
            luck=5,
        ),
        # Экипировка дает доп. защиту и урон
        "fixed_loadout": MonsterLoadout(main_hand="spear", off_hand="shield", chest_armor="jerkin"),
        "skills": ["attack_pierce", "buff_defense"],
    },
    "bandit_cutthroat_training": {
        "id": "bandit_cutthroat_training",
        "name_ru": "Бандит-головорез",
        "role": "veteran",
        "narrative_hint": "A quick and ruthless fighter with two daggers.",
        "description": "Изгнанник, нашедший приют в тенях Разлома. Он не следует кодексу чести, предпочитая удар в спину честному поединку. Его кинжалы смазаны ядом, а движения быстры и непредсказуемы.",
        "combat_intro_text": "Бандит ухмыляется, поигрывая кинжалами. Его глаза бегают, ища уязвимое место в твоей защите.",
        "cost": 50,
        "extra_tags": ["human", "outlaw", "training"],
        "base_stats": MonsterStats(
            strength=9,
            agility=16,  # Высокая ловкость для уклонения (легкая броня)
            endurance=8,
            intelligence=6,
            wisdom=4,
            men=8,
            perception=10,
            charisma=3,
            luck=12,
        ),
        "fixed_loadout": MonsterLoadout(
            main_hand="dagger",
            off_hand="dagger",
            chest_armor="jerkin",
            gloves_garment="work_gloves",
            belt_accessory="belt",
        ),
        "skills": ["poison_stab", "evasion"],
    },
    "goblin_slinger_training": {
        "id": "goblin_slinger_training",
        "name_ru": "Гоблин-пращник",
        "role": "veteran",
        "narrative_hint": "A fast goblin with a sling. Keeps distance.",
        "description": "Мелкий и юркий гоблин, предпочитающий держаться подальше от драки. Его праща посылает камни с убийственной точностью, способной проломить череп зазевавшемуся путнику.",
        "combat_intro_text": "Гоблин-пращник раскручивает пращу над головой, держа дистанцию и злобно хихикая.",
        "cost": 50,
        "extra_tags": ["ranged", "fast", "training"],
        "base_stats": MonsterStats(
            strength=6,
            agility=15,  # Подняли ловкость, так как броня легкая
            endurance=10,
            intelligence=6,
            wisdom=7,
            men=5,
            perception=12,
            charisma=4,
            luck=7,
        ),
        # Исправлено: Добавлена праща и простая одежда
        "fixed_loadout": MonsterLoadout(main_hand="sling", chest_garment="shirt", legs_garment="trousers"),
        "skills": ["attack_ranged"],
    },
    # ==================================================
    # ЗВЕРИ (Статы ВЫШЕ, так как нет вещей)
    # ==================================================
    "wolf_stalker_training": {
        "id": "wolf_stalker_training",
        "name_ru": "Волк-сталкер",
        "role": "veteran",
        "narrative_hint": "A wolf that moves low to the ground. Stronger than an armed goblin naturally.",
        "description": "Хищник, мутировавший под влиянием энергии Разлома. Он движется почти бесшумно, прижимаясь к земле. Его шкура прочнее обычной кожи, а инстинкты обострены до предела.",
        "combat_intro_text": "Волк-сталкер выходит из тени, низко пригнув голову. Его желтые глаза светятся голодом.",
        "cost": 50,
        "extra_tags": ["stealth", "hunter", "training"],
        "base_stats": MonsterStats(
            strength=14,  # +4 к силе по сравнению с гоблином (компенсация оружия)
            agility=14,  # Высокая ловкость
            endurance=15,  # +4 к выносливости (природная шкура вместо брони)
            intelligence=5,
            wisdom=4,
            men=7,
            perception=14,
            charisma=3,
            luck=5,
        ),
        "fixed_loadout": MonsterLoadout(),
        "skills": ["attack_heavy"],
    },
    "wolf_flanker_training": {
        "id": "wolf_flanker_training",
        "name_ru": "Волк-фланкер",
        "role": "veteran",
        "narrative_hint": "A clever wolf that attacks from behind.",
        "description": "Этот волк специализируется на тактике стаи. Он всегда пытается зайти сбоку или со спины, отвлекая внимание жертвы. Его скорость позволяет ему избегать большинства ударов.",
        "combat_intro_text": "Волк-фланкер начинает кружить вокруг тебя, выискивая момент для броска.",
        "cost": 50,
        "extra_tags": ["tactical", "fast", "training"],
        "base_stats": MonsterStats(
            strength=13,
            agility=16,  # Очень быстрый
            endurance=14,
            intelligence=6,
            wisdom=4,
            men=8,
            perception=12,
            charisma=4,
            luck=5,
        ),
        "fixed_loadout": MonsterLoadout(),
        "skills": ["attack_fast", "debuff_weaken"],
    },
    "wolf_snapper_training": {
        "id": "wolf_snapper_training",
        "name_ru": "Волк-кусака",
        "role": "veteran",
        "narrative_hint": "A wolf with powerful jaws. Hits very hard.",
        "description": "Массивная тварь с гипертрофированными челюстями. Он не прячется и не хитрит — он просто идет напролом, чтобы сомкнуть зубы на горле жертвы. Один его укус может стать фатальным.",
        "combat_intro_text": "Волк-кусака рычит, обнажая ряды острых как бритва зубов. С его клыков капает слюна.",
        "cost": 50,
        "extra_tags": ["executioner", "strong_jaw", "training"],
        "base_stats": MonsterStats(
            strength=16,  # Очень сильный укус
            agility=12,
            endurance=16,  # Живучий
            intelligence=4,
            wisdom=3,
            men=8,
            perception=10,
            charisma=3,
            luck=5,
        ),
        "fixed_loadout": MonsterLoadout(),
        "skills": ["attack_execute", "debuff_stun"],
    },
}

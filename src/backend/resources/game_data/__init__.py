"""
Game Data Library - Unified Public API
======================================

Этот модуль предоставляет единую точку входа (Facade) для доступа ко всем статическим данным игры:
навыкам, предметам, способностям, эффектам и т.д.

Вместо того чтобы импортировать функции из каждого подмодуля отдельно:
    from src.backend.resources.game_data.skills import get_skill_config
    from src.backend.resources.game_data.items import get_item_data

Используйте единый класс GameData:
    from src.backend.resources.game_data import GameData

    skill = GameData.get_skill("skill_swords")
    item = GameData.get_item("sword")
"""

# Импорт геттеров из подмодулей
from .abilities import get_ability_config, get_all_abilities
from .effects import get_all_effects, get_effect_config
from .feints import get_all_feints, get_feint_config
from .gifts import get_all_gifts, get_gift_config
from .items import get_item_data
from .skills import get_all_skills, get_skill_config
from .triggers import get_all_triggers, get_weapon_trigger


class GameData:
    """
    Единый фасад для доступа ко всем игровым данным.
    Все методы статические.
    """

    # --- SKILLS ---
    get_skill = staticmethod(get_skill_config)
    get_all_skills = staticmethod(get_all_skills)

    # --- GIFTS ---
    get_gift = staticmethod(get_gift_config)
    get_all_gifts = staticmethod(get_all_gifts)

    # --- ITEMS ---
    get_item = staticmethod(get_item_data)
    # Note: Items have complex API (crafting, loot), exposed directly in items module if needed.

    # --- ABILITIES ---
    get_ability = staticmethod(get_ability_config)
    get_all_abilities = staticmethod(get_all_abilities)

    # --- EFFECTS ---
    get_effect = staticmethod(get_effect_config)
    get_all_effects = staticmethod(get_all_effects)

    # --- TRIGGERS ---
    get_trigger = staticmethod(get_weapon_trigger)
    get_all_triggers = staticmethod(get_all_triggers)

    # --- FEINTS ---
    get_feint = staticmethod(get_feint_config)
    get_all_feints = staticmethod(get_all_feints)


__all__ = ["GameData"]

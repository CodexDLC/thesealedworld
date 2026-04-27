"""
Пресеты мутаций для Абилок.
Позволяют быстро настроить поведение Пайплайна (Атака, Хил, Бафф).
"""

from typing import Any

PIPELINE_PRESETS: dict[str, dict[str, Any]] = {
    # === MAGIC ATTACK (Магическая Атака) ===
    # Использует магические статы, проверяет резисты.
    "MAGIC_ATTACK": {
        "meta.source_type": "magic",
        "stages.check_accuracy": True,
        "stages.check_evasion": True,  # Можно увернуться? (Обычно да)
        "stages.check_parry": False,  # Магию нельзя парировать мечом
        "stages.check_block": False,  # Магию нельзя блокировать щитом (обычным)
        "stages.calculate_damage": True,
    },
    # === HEALING (Лечение) ===
    # Пропускает боевые проверки, считает только хил.
    "HEALING": {
        "meta.source_type": "magic",
        "stages.check_accuracy": False,
        "stages.check_evasion": False,
        "stages.check_parry": False,
        "stages.check_block": False,
        "stages.check_crit": True,  # Хил может критовать
        "stages.calculate_damage": False,
        "stages.calculate_healing": True,  # Включаем расчет хила
    },
    # === BUFF / DEBUFF (Чистый эффект) ===
    # Пропускает всё, кроме применения эффектов.
    "BUFF": {
        "phases.run_calculator": False,  # Выключаем Резолвер полностью
        "phases.run_stats_engine": True,  # Статы нужны для скейлинга эффектов
    },
    # === WEAPON SKILL (Навык Оружия) ===
    # Ведет себя как обычная атака, но может иметь бонусы.
    "WEAPON_SKILL": {
        "meta.source_type": "main_hand",
        # Все этапы включены по умолчанию в Pipeline
    },
    # === UNBLOCKABLE (Неблокируемая Атака) ===
    "UNBLOCKABLE": {
        "restriction.ignore_block": True,
        "restriction.ignore_parry": True,
    },
}

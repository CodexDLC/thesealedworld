"""
Пресеты мутаций для Абилок.
Позволяют быстро настроить поведение Пайплайна (Атака, Хил, Бафф).
"""

from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import (
    PipelineMutationApplicationDTO,
    pipeline_mutation,
)

PIPELINE_PRESETS: dict[str, list[PipelineMutationApplicationDTO]] = {
    # === MAGIC ATTACK (Магическая Атака) ===
    # Использует магические статы, проверяет резисты.
    "MAGIC_ATTACK": [
        pipeline_mutation("meta.source_type", "magic"),
        pipeline_mutation("stage.check_accuracy", True),
        pipeline_mutation("stage.check_evasion", True),
        pipeline_mutation("stage.check_parry", False),
        pipeline_mutation("stage.check_block", False),
        pipeline_mutation("stage.calculate_damage", True),
    ],
    # === HEALING (Лечение) ===
    # Пропускает боевые проверки, считает только хил.
    "HEALING": [
        pipeline_mutation("meta.source_type", "magic"),
        pipeline_mutation("stage.check_accuracy", False),
        pipeline_mutation("stage.check_evasion", False),
        pipeline_mutation("stage.check_parry", False),
        pipeline_mutation("stage.check_block", False),
        pipeline_mutation("stage.check_crit", True),
        pipeline_mutation("stage.calculate_damage", False),
        pipeline_mutation("stage.calculate_healing", True),
    ],
    # === BUFF / DEBUFF (Чистый эффект) ===
    # Пропускает всё, кроме применения эффектов.
    "BUFF": [
        pipeline_mutation("phase.run_calculator", False),
        pipeline_mutation("phase.run_stats_engine", True),
    ],
    # === WEAPON SKILL (Навык Оружия) ===
    # Ведет себя как обычная атака, но может иметь бонусы.
    "WEAPON_SKILL": [
        pipeline_mutation("meta.source_type", "main_hand"),
    ],
    # === UNBLOCKABLE (Неблокируемая Атака) ===
    "UNBLOCKABLE": [
        pipeline_mutation("ignore_block"),
        pipeline_mutation("ignore_parry"),
    ],
}

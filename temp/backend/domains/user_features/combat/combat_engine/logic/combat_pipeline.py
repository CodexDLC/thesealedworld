from typing import Any

from src.backend.domains.user_features.combat.combat_engine.logic.ability_service import AbilityService
from src.backend.domains.user_features.combat.combat_engine.logic.combat_resolver import CombatResolver
from src.backend.domains.user_features.combat.combat_engine.logic.context_builder import ContextBuilder
from src.backend.domains.user_features.combat.combat_engine.logic.mechanics_service import (
    MechanicsService,
)
from src.backend.domains.user_features.combat.combat_engine.logic.stats_engine import StatsEngine
from src.backend.domains.user_features.combat.dto import (
    ActorSnapshot,
    CombatMoveDTO,
    InteractionResultDTO,
    PipelineContextDTO,
)


class CombatPipeline:
    """
    Оркестратор боевого взаимодействия (Combat Pipeline).
    Выполняет полный цикл обработки одного удара/действия.
    """

    def __init__(self):
        self.ability_service = AbilityService()
        self.mechanics_service = MechanicsService()
        # Resolver и ContextBuilder - статические/без состояния

    async def calculate(
        self,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        move: CombatMoveDTO,
        exchange_count: int = 0,
        external_mods: dict[str, Any] | None = None,
    ) -> InteractionResultDTO:
        """
        Запуск пайплайна (Async).
        """
        # 0. Context Build
        # ContextBuilder создает ctx и инициализирует ctx.result (заполняет ID и hand)
        ctx = ContextBuilder.build_context(source, target, move, external_mods)

        # 1. Pre-Calculation (Ability Service)
        if ctx.phases.run_pre_calc:
            # AbilityService теперь берет result из ctx.result
            self.ability_service.pre_process(ctx, move, source, target)

        # 1.5. Liveness Check (Управление флагами)
        if ctx.phases.run_calculator:
            self._check_liveness(ctx, source, target)

        # 2. Stats Calculation (Stats Engine)
        if ctx.phases.run_calculator:
            StatsEngine.ensure_stats(source)
            if target:
                StatsEngine.ensure_stats(target)

        # 3. Calculator (Resolver)
        if ctx.phases.run_calculator and target and source.stats and target.stats:
            # Resolver работает напрямую с ctx.result
            CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

        # 4. Post-Calculation (Ability Service)
        if ctx.phases.run_post_calc:
            # AbilityService использует ctx.result
            self.ability_service.post_process(ctx, source, target, move)

        # 5. Mechanics (Apply Results & Logs)
        # Исправлен порядок аргументов: ctx, source, target, result
        self.mechanics_service.apply_interaction_result(ctx, source, target, ctx.result)

        return ctx.result

    def _check_liveness(self, ctx: PipelineContextDTO, source: ActorSnapshot, target: ActorSnapshot | None) -> None:
        """
        Проверяет, живы ли участники.
        Если нет - отключает фазу калькуляции и пост-процессинга.
        """
        if not source.is_alive:
            ctx.phases.run_calculator = False
            ctx.phases.run_post_calc = False
            return

        if target and not target.is_alive:
            ctx.phases.run_calculator = False
            ctx.phases.run_post_calc = False

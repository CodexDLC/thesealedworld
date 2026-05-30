from loguru import logger as log

from src.backend.features.combat.dto.session import BattleMeta


class VictoryChecker:
    """
    Сервис проверки условий победы в боевой сессии.

    v2.0: Работает с BattleMeta из RBC v3.0.
    """

    @staticmethod
    def check_battle_end(meta: BattleMeta) -> str | None:
        """
        Проверяет, завершился ли бой, и определяет победителя.

        Args:
            meta: Метаданные боевой сессии (teams, dead_actors).

        Returns:
            Строка с названием победившей команды ('blue', 'red'),
            'draw' в случае ничьей, или None, если бой продолжается.
        """
        # Конвертируем dead_actors в set для O(1) lookup
        dead_set = set(str(x) for x in meta.dead_actors)
        alive_teams = set()

        for team_name, members in meta.teams.items():
            # Команда жива, если хотя бы один участник НЕ в списке мертвых
            if any(str(m) not in dead_set for m in members):
                alive_teams.add(team_name)

        if len(alive_teams) == 0:
            log.bind(result="draw").info("VictoryCheckerBattleEnded")
            return "draw"
        elif len(alive_teams) == 1:
            winner_team = list(alive_teams)[0]
            log.bind(result="victory", winner_team=winner_team).info("VictoryCheckerBattleEnded")
            return winner_team

        log.trace("VictoryCheckerBattleContinues")
        return None

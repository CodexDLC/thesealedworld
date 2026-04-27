# # apps/game_core/modules/combats/core/combat_xp_manager.py
# from loguru import logger as log
#
# from apps.shared.schemas_dto import CombatSessionContainerDTO
# from apps.game_core.resources.game_data.xp_rules import BASE_ACTION_XP, OUTCOME_MULTIPLIERS, XP_SOURCE_MAP
#
#
# class CombatXPManager:
#     """
#     Сервис для расчета и накопления опыта (XP) в процессе боя.
#
#     Отвечает за определение количества опыта, получаемого актором за
#     различные боевые действия, и сохранение его во временном буфере.
#     Не взаимодействует напрямую с базой данных.
#     """
#
#     @staticmethod
#     def register_action(actor: CombatSessionContainerDTO, item_subtype: str, outcome: str) -> None:
#         """
#         Рассчитывает опыт за боевое действие и добавляет его в буфер опыта актора.
#
#         Args:
#             actor: DTO актора, совершившего действие.
#             item_subtype: Подтип предмета или действия (например, "sword", "shield", "light_armor").
#             outcome: Результат действия ("success", "miss", "crit", "partial").
#         """
#         if not actor.state:
#             log.warning(f"CombatXPManager | status=failed reason='Actor state missing' actor_id={actor.char_id}")
#             return
#
#         skill_key = XP_SOURCE_MAP.get(item_subtype)
#         if not skill_key:
#             log.warning(
#                 f"CombatXPManager | status=skipped reason='No skill mapping for subtype' subtype='{item_subtype}' actor_id={actor.char_id}"
#             )
#             return
#
#         mult = OUTCOME_MULTIPLIERS.get(outcome, 0.0)
#         if mult == 0:
#             log.trace(
#                 f"CombatXPManager | status=skipped reason='Zero multiplier for outcome' outcome='{outcome}' actor_id={actor.char_id}"
#             )
#             return
#
#         raw_points = int(BASE_ACTION_XP * mult)
#         current_xp = actor.state.xp_buffer.get(skill_key, 0)
#         actor.state.xp_buffer[skill_key] = current_xp + raw_points
#
#         log.trace(
#             f"CombatXPManager | event=xp_added actor_id={actor.char_id} skill='{skill_key}' outcome='{outcome}' points={raw_points} total={actor.state.xp_buffer[skill_key]}"
#         )

# # apps/game_core/modules/combats/core/combat_log_builder.py
# # Refactored for RBC v3.0
# import random
#
# from apps.game_core.modules.combat.dto.combat_pipeline_dto import InteractionResultDTO
# from apps.game_core.resources.game_data.combat_flavor import COMBAT_PHRASES
#
#
# class CombatLogBuilder:
#     """
#     Сервис для формирования человеко-читаемых записей лога боя.
#     Адаптирован под RBC v3.0 (InteractionResultDTO).
#     """
#
#     @staticmethod
#     def build_duel_log(
#         attacker_name: str,
#         defender_name: str,
#         result: InteractionResultDTO,
#         defender_hp: int,
#         defender_energy: int,
#     ) -> str:
#         """
#         Строит лог для одиночного удара (Exchange/Instant).
#         """
#         # 1. Visual Bar (генерируется в Calculator, но здесь мы его форматируем)
#         # В DTO логи лежат в result.logs, и первый элемент может быть баром
#         # Но лучше, если Calculator возвращает чистые данные, а Builder строит строку.
#         # В текущем Calculator visual_bar лежит в logs[0] (если включен).
#         # Давайте извлечем его.
#
#         parts = []
#
#         # Если в логах есть бар, берем его
#         if result.logs and "[" in result.logs[0]:
#              parts.append(result.logs[0])
#              extra_logs = result.logs[1:]
#         else:
#              extra_logs = result.logs
#
#         # 2. Main Phrase
#         phrase_key = CombatLogBuilder._get_phrase_key(result)
#         templates = COMBAT_PHRASES.get(phrase_key, COMBAT_PHRASES["hit"])
#         template = random.choice(templates)
#
#         text = template.format(
#             attacker=attacker_name,
#             defender=defender_name,
#             damage=result.damage_final
#         )
#
#         if not result.is_dodged:
#             text += f" <b>({defender_hp} HP | {defender_energy} EN)</b>"
#
#         parts.append(text)
#
#         # 3. Shield Break
#         if result.shield_dmg > 0 and result.damage_final > 0:
#             parts.append(random.choice(COMBAT_PHRASES.get("shield_break", ["Щит пробит!"])).format(defender=defender_name))
#
#         # 4. Lifesteal
#         if result.lifesteal_amount > 0:
#             parts.append(f"💚 <b>{attacker_name}</b> восстановил {result.lifesteal_amount} HP.")
#
#         # 5. Extra Logs (Buffs, Crits details)
#         if extra_logs:
#             parts.extend(extra_logs)
#
#         return " ".join(parts)
#
#     @staticmethod
#     def build_mass_log(
#         source_name: str,
#         results: list[tuple[str, InteractionResultDTO]] # [(TargetName, Result), ...]
#     ) -> str:
#         """
#         Строит агрегированный лог для массовой атаки.
#         Пример: "Маг кастует Огненный дождь! Орк: -10 HP. Элф: Уворот."
#         """
#         parts = [f"<b>{source_name}</b> проводит массовую атаку!"]
#
#         for target_name, res in results:
#             if res.is_dodged:
#                 parts.append(f"{target_name}: 💨 Уворот")
#             elif res.damage_final > 0:
#                 parts.append(f"{target_name}: -{res.damage_final} HP")
#             elif res.is_blocked:
#                 parts.append(f"{target_name}: 🛡️ Блок")
#             else:
#                 parts.append(f"{target_name}: Эффект наложен")
#
#         return " | ".join(parts)
#
#     @staticmethod
#     def _get_phrase_key(result: InteractionResultDTO) -> str:
#         if result.is_dodged:
#             return "dodge"
#         if result.is_parried:
#             return "parry"
#         if result.is_crit:
#             return "crit"
#         if result.is_blocked and result.damage_final == 0:
#             return "block_full"
#         return "hit"

# from typing import Any, Protocol
#
# from apps.shared.schemas_dto.game_state_enum import GameState
# from loguru import logger as log
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from backend.database.redis.manager.account_manager import AccountManager
# from backend.database.redis.redis_fields import AccountFields as Af
#
#
# class GameOrchestratorProto(Protocol):
#     """Контракт: любой оркестратор должен уметь бэкапить свою сессию."""
#
#     async def backup_session(self, char_id: int, db: AsyncSession) -> None: ...
#
#
# class SessionSyncDispatcher:
#     """
#     Диспетчер-мусорщик. Вызывается в конце каждого стартового метода Backend-роутов.
#     """
#
#     def __init__(self, account_manager: AccountManager, registry: dict[str, Any]):
#         self.am = account_manager
#         # Реестр: поле_в_ac -> оркестратор
#         self._registry = registry
#
#     async def sync(self, char_id: int, db: AsyncSession) -> None:
#         """
#         Основной метод синхронизации. Проверяет 'брошенные' сессии.
#         """
#         # 1. Забираем ядро из Redis
#         ac_data = await self.am.get_account_data(char_id)
#         if not ac_data:
#             return
#
#         current_state = ac_data.get(Af.STATE)
#
#         # 2. Маппинг: Ключ в ac:{char_id} -> Стейт, которому он принадлежит
#         watch_map = {
#             Af.INVENTORY_SESSION_ID: GameState.INVENTORY,
#             Af.SCENARIO_SESSION_ID: GameState.SCENARIO,
#             Af.COMBAT_SESSION_ID: GameState.COMBAT,
#         }
#
#         for field, state_name in watch_map.items():
#             session_id = ac_data.get(field)
#             if not session_id:
#                 continue
#
#             # Если мы НЕ в том состоянии, сессия которого активна — пора чистить
#             if current_state != state_name:
#                 orch = self._registry.get(field)
#                 if orch:
#                     log.info(f"Sync | Backing up orphan session: {field} for char {char_id}")
#                     # Делегируем бэкап самому оркестратору
#                     await orch.backup_session(char_id, db)

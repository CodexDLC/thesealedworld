# apps/game_core/system/context_assembler/logic/monster_assembler.py
import uuid
from typing import Any

from loguru import logger as log
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.postgres.repositories.monster_repository import MonsterRepository
from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.database.redis.manager.context_manager import ContextRedisManager
from src.backend.domains.internal_systems.context_assembler.logic.base_assembler import BaseAssembler
from src.backend.domains.internal_systems.context_assembler.schemas.monster_temp_context import MonsterTempContextSchema


class MonsterAssembler(BaseAssembler):
    """
    Стратегия сборки контекста для Монстров.
    """

    def __init__(self, session: AsyncSession, account_manager: AccountManager, context_manager: ContextRedisManager):
        self.session = session
        self.account_manager = account_manager
        self.context_manager = context_manager
        self.monster_repo = MonsterRepository(session)

    async def process_batch(self, ids: list[Any], scope: str) -> tuple[dict[Any, str], list[Any]]:
        """
        Пакетная обработка монстров.
        """
        log.debug(f"MonsterAssembler | processing batch count={len(ids)} scope={scope}")

        if not ids:
            return {}, []

        # Ensure ids are strings
        str_ids = [str(i) for i in ids]

        try:
            monsters_orm = await self.monster_repo.get_monsters_batch(str_ids)
        except Exception as e:  # noqa: BLE001
            log.exception(f"MonsterAssembler | DB fetch failed. Error: {e}")
            return {}, str_ids

        monsters_map = {str(m.id): m for m in monsters_orm}

        success_map = {}
        error_list = []
        contexts_to_save = {}

        for m_id in str_ids:
            monster_orm = monsters_map.get(m_id)
            if not monster_orm:
                error_list.append(m_id)
                continue

            try:
                # Используем MonsterTempContextSchema
                context_schema = MonsterTempContextSchema(
                    core_stats=monster_orm.scaled_base_stats,
                    core_loadout=monster_orm.loadout_ids,
                    core_skills=monster_orm.skills_snapshot,
                    core_meta={
                        "id": m_id,
                        "name": monster_orm.name_ru,  # Используем name_ru как основное имя
                        "role": monster_orm.role,
                        "threat": monster_orm.threat_rating,
                        "clan_id": str(monster_orm.clan_id),
                    },
                )

                context_data = context_schema.model_dump(
                    by_alias=True,
                    exclude={
                        "core_stats",
                        "core_loadout",
                        "core_skills",
                        "core_meta",
                    },
                )

                redis_key = f"temp:setup:{uuid.uuid4()}"
                success_map[m_id] = redis_key
                contexts_to_save[m_id] = (redis_key, context_data)
            except Exception as e:  # noqa: BLE001
                log.error(f"MonsterAssembler | transform failed for {m_id}: {e}")
                error_list.append(m_id)

        # 3. Массовое сохранение с детальной обработкой ошибок
        if contexts_to_save:
            try:
                # TODO: Рефакторинг ContextRedisManager - удалить атрибут .redis
                # Проблема: Старый API context_manager.redis.redis_client (legacy)
                # Решение: Использовать новый RedisService напрямую или обновить ContextRedisManager
                # Используем pipeline БЕЗ transaction для performance
                async with self.context_manager.redis.redis_client.pipeline(transaction=False) as pipe:  # type: ignore[attr-defined]
                    # Словарь для маппинга индексов результатов к m_id
                    index_to_monster = {}
                    idx = 0

                    for m_id, (redis_key, context_data) in contexts_to_save.items():
                        pipe.json().set(redis_key, "$", context_data)
                        pipe.expire(redis_key, 3600)
                        index_to_monster[idx] = m_id
                        idx += 2  # каждая операция генерирует 2 команды

                    # Выполняем pipeline с raise_on_error=False для обработки частичных сбоев
                    results = await pipe.execute(raise_on_error=False)

                    # Проверяем результаты каждой пары операций (set + expire)
                    for i, m_id in index_to_monster.items():
                        set_result = results[i]  # json().set
                        expire_result = results[i + 1]  # expire

                        # Если хотя бы одна операция неудачна, считаем m_id ошибочным
                        if isinstance(set_result, Exception) or isinstance(expire_result, Exception):
                            log.error(
                                f"MonsterAssembler | save failed for {m_id}. Set: {set_result}, Expire: {expire_result}"
                            )
                            error_list.append(m_id)
                            # Убираем из success_map, если был добавлен ранее
                            success_map.pop(m_id, None)
                        # Если обе операции успешны, m_id уже в success_map

            except (RedisError, OSError) as e:
                # Катастрофический сбой (например, Redis недоступен)
                log.critical(f"MonsterAssembler | Redis catastrophic failure: {e}")
                # В этом случае помечаем все как ошибки
                for m_id in contexts_to_save:
                    if m_id not in error_list:
                        error_list.append(m_id)
                    success_map.pop(m_id, None)

        log.info(f"MonsterAssembler | batch processed. success={len(success_map)}, errors={len(error_list)}")
        return success_map, error_list

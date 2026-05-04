# apps/game_core/system/context_assembler/logic/player_assembler.py
import asyncio
from typing import Any, cast

from loguru import logger as log
from pydantic import ValidationError
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.postgres.models.symbiote import CharacterSymbiote
from src.backend.database.postgres.repositories import (
    get_character_attributes_repo,
    get_character_repo,
    get_inventory_repo,
    get_skill_progress_repo,
    get_symbiote_repo,
)
from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.database.redis.manager.context_manager import ContextRedisManager
from src.backend.database.redis.manager.inventory_manager import InventoryManager
from src.backend.domains.internal_systems.context_assembler.logic.base_assembler import BaseAssembler
from src.backend.domains.internal_systems.context_assembler.logic.context_session_manager import ContextSessionManager
from src.backend.domains.internal_systems.context_assembler.logic.query_plan import get_query_plan
from src.backend.domains.internal_systems.context_assembler.schemas.base import BaseTempContext
from src.backend.domains.internal_systems.context_assembler.schemas.combat import CombatTempContext
from src.backend.domains.internal_systems.context_assembler.schemas.inventory import InventoryTempContext
from src.backend.domains.internal_systems.context_assembler.schemas.status import StatusTempContext
from src.shared.schemas.character import CharacterAttributesReadDTO, CharacterReadDTO
from src.shared.schemas.skill import SkillProgressDTO


class PlayerAssembler(BaseAssembler):
    """
    Стратегия сборки контекста для Игроков.
    Собирает данные из PostgreSQL (Attributes, Inventory, Skills) и формирует JSON для Redis.
    """

    def __init__(
        self,
        session: AsyncSession,
        account_manager: AccountManager,
        context_manager: ContextRedisManager,
        inventory_manager: InventoryManager,  # Добавлено
    ):
        self.session = session
        self.account_manager = account_manager
        # Используем новый фасад
        self.session_manager = ContextSessionManager(context_manager, inventory_manager)  # Передаем inventory_manager
        self.char_repo = get_character_repo(session)
        self.attributes_repo = get_character_attributes_repo(session)
        self.inv_repo = get_inventory_repo(session)
        self.skill_repo = get_skill_progress_repo(session)
        self.symbiote_repo = get_symbiote_repo(session)

    async def process_batch(self, ids: list[Any], scope: str) -> tuple[dict[Any, str], list[Any]]:
        """
        Реализация пакетной обработки игроков.
        """
        log.debug(f"PlayerAssembler | processing batch count={len(ids)} scope={scope}")

        if not ids:
            return {}, []

        int_ids = [int(i) for i in ids]
        query_plan = get_query_plan(scope)

        # 1. Пакетный сбор данных (Conditional Loading)
        tasks: list[Any] = []  # type: ignore[var-annotated]
        task_mapping = []

        # Всегда грузим базовую инфу о персонаже (для meta)
        tasks.append(self.char_repo.get_characters_batch(int_ids))
        task_mapping.append("char")

        if "attributes" in query_plan:
            tasks.append(self.attributes_repo.get_attributes_batch(int_ids))
            task_mapping.append("attributes")

        if "inventory" in query_plan:
            # Всегда грузим весь инвентарь (equipped + inventory)
            t1 = self.inv_repo.get_items_by_location_batch(int_ids, "equipped")
            t2 = self.inv_repo.get_items_by_location_batch(int_ids, "inventory")
            tasks.append(asyncio.gather(t1, t2))
            task_mapping.append("inventory_complex")

        if "skills" in query_plan:
            tasks.append(self.skill_repo.get_all_skills_progress_batch(int_ids))
            task_mapping.append("skills")

        if "vitals" in query_plan:
            tasks.append(self.account_manager.get_accounts_json_batch(int_ids, "vitals"))
            task_mapping.append("vitals")

        if "symbiote" in query_plan:
            tasks.append(self.symbiote_repo.get_symbiotes_batch(int_ids))
            task_mapping.append("symbiote")

        # Ждем всех
        try:
            results = await asyncio.gather(*tasks)
        except (SQLAlchemyError, RedisError, OSError) as e:
            log.exception(f"PlayerAssembler | DB fetch failed for batch. Error: {e}")
            return {}, int_ids

        # Распаковка результатов
        raw_data: dict[str, Any] = {}
        for key, result in zip(task_mapping, results, strict=False):
            if key == "inventory_complex":
                equipped, inventory = result  # type: ignore[misc]
                combined = {}
                for cid in int_ids:
                    combined[cid] = equipped.get(cid, []) + inventory.get(cid, [])  # type: ignore[attr-defined]
                raw_data["inventory"] = combined
            else:
                raw_data[key] = result

        # Преобразование в словари по ID
        chars_map = {char.character_id: char for char in cast("list[CharacterReadDTO]", raw_data.get("char", []))}
        attributes_map = {
            attr.character_id: attr for attr in cast("list[CharacterAttributesReadDTO]", raw_data.get("attributes", []))
        }
        skills_map = cast("dict[int, list[SkillProgressDTO]]", raw_data.get("skills", {}))
        inventory_map = cast("dict[int, list[Any]]", raw_data.get("inventory", {}))
        symbiotes_map = {s.character_id: s for s in cast("list[CharacterSymbiote]", raw_data.get("symbiote", []))}

        # Vitals приходят списком в порядке ID
        vitals_list = cast("list[dict | None]", raw_data.get("vitals", []))
        vitals_map = {}
        if "vitals" in query_plan:
            vitals_map = {char_id: vitals for char_id, vitals in zip(int_ids, vitals_list, strict=False)}

        # 2. Трансформация и подготовка к сохранению
        error_list = []
        contexts_to_save: dict[int, dict[str, Any]] = {}

        # Выбор класса DTO
        dto_class = self._select_dto_class(scope)

        for char_id in int_ids:
            if char_id not in chars_map:
                error_list.append(char_id)
                continue

            try:
                # Сборка данных для конкретного персонажа
                char_info = chars_map.get(char_id)
                attributes = attributes_map.get(char_id)
                skills = skills_map.get(char_id)
                inventory = inventory_map.get(char_id)  # type: ignore[assignment]
                vitals = vitals_map.get(char_id)
                symbiote = symbiotes_map.get(char_id)

                symbiote_data = None
                if symbiote:
                    symbiote_data = {
                        "symbiote_name": symbiote.symbiote_name,
                        "gift_id": symbiote.gift_id,
                        "gift_rank": symbiote.gift_rank,
                        "gift_xp": symbiote.gift_xp,
                        "elements_resonance": symbiote.elements_resonance,
                    }

                # Создание контекста
                context_schema = dto_class(  # type: ignore[arg-type]
                    core_meta=char_info,
                    core_attributes=attributes,
                    core_inventory=inventory,
                    core_skills=skills,
                    core_vitals=vitals,
                    core_symbiote=symbiote_data,
                )

                # Сериализация (exclude убирает core_* поля)
                context_data = context_schema.model_dump(
                    by_alias=True,
                    exclude={
                        "core_attributes",
                        "core_inventory",
                        "core_skills",
                        "core_vitals",
                        "core_meta",
                        "core_symbiote",
                        "core_wallet",
                    },
                )

                # Собираем данные для сохранения
                contexts_to_save[char_id] = context_data

            except (ValidationError, ValueError, TypeError) as e:
                log.error(f"PlayerAssembler | transform failed for {char_id}: {e}")
                error_list.append(char_id)

        # 3. Массовое сохранение через Фасад (ContextSessionManager)
        success_map = {}
        if contexts_to_save:
            try:
                # Фасад сам решит, какие ключи использовать и как сохранять
                success_map = await self.session_manager.save_player_batch(scope, contexts_to_save)
            except Exception as e:  # noqa: BLE001
                log.error(f"PlayerAssembler | batch save failed: {e}")
                # Если сохранение упало, считаем всех ошибочными
                for char_id in contexts_to_save:
                    if char_id not in error_list:
                        error_list.append(char_id)

        log.info(f"PlayerAssembler | batch processed. success={len(success_map)}, errors={len(error_list)}")
        return success_map, error_list

    def _select_dto_class(self, scope: str) -> type[BaseTempContext]:
        if scope == "combats":
            return CombatTempContext
        if scope == "status":
            return StatusTempContext
        if scope == "inventory":
            return InventoryTempContext
        return BaseTempContext

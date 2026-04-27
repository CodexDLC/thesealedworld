import asyncio
import json
from typing import Any
from uuid import uuid4

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.postgres.models import GeneratedClanORM, GeneratedMonsterORM
from src.backend.database.postgres.repositories import MonsterRepository
from src.backend.domains.internal_systems.factories.monster.clan_hashing import (
    compute_context_hash,
    compute_unique_clan_hash,
    normalize_tags,
)
from src.backend.resources.game_data.monsters import get_available_variants_for_tier, get_family_config
from src.backend.resources.game_data.monsters.spawn_config import (
    BIOME_FAMILIES,
    TIER_AVAILABILITY,
    TIER_SCALING_CONFIG,
)
from src.backend.services.gemini_service.gemini_service import gemini_answer
from src.shared.schemas.monster_dto import MonsterFamilyDTO, MonsterVariantDTO


class ClanFactory:
    """
    Фабрика для создания 'Таблиц Встреч' (Encounter Pools).
    Генерирует ВСЕ возможные варианты кланов для заданных условий.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MonsterRepository(session)
        self._llm_semaphore = asyncio.Semaphore(3)
        # Кэш: Key = hash_контекста_плюс_семья, Value = ClanORM
        self.context_cache: dict[str, GeneratedClanORM] = {}
        log.debug("ClanFactoryInit")

    async def ensure_population_for_zone(self, tier: int, biome_id: str, location_tags: list[str], zone_id: str):
        """
        Гарантирует, что для текущего биома и тира в БД существуют кланы ВСЕХ доступных типов.
        """
        # 1. Получаем список ВСЕХ возможных кандидатов (Крысы, Бандиты, Пауки...)
        candidates = self._select_candidates(tier, biome_id)

        if not candidates:
            return

        # 2. Нормализуем теги (Context Hash)
        clean_tags = normalize_tags(location_tags)
        # Хеш зависит ТОЛЬКО от условий среды (Биом + Тир + Теги).
        # zone_id здесь НЕ участвует, так как кланы общие для всех зон с таким климатом.
        context_hash_base = compute_context_hash(tier, biome_id, clean_tags)

        # 3. ЦИКЛ ПО ВСЕМ КАНДИДАТАМ (Генерируем пул)
        # Мы не выбираем одного. Мы должны убедиться, что существуют ВСЕ.
        for family_id in candidates:
            await self._ensure_specific_family_exists(
                family_id=family_id,
                tier=tier,
                clean_tags=clean_tags,
                context_hash_base=context_hash_base,
                zone_id=zone_id,  # Используется только как "место рождения" для логов
            )

    async def _ensure_specific_family_exists(
        self, family_id: str, tier: int, clean_tags: list[str], context_hash_base: str, zone_id: str
    ):
        # Формируем уникальный ключ для кэша/проверки: "Контекст + Семейство"
        # Пример: "ruins_t1_tags_HASH_bandits"
        specific_cache_key = f"{context_hash_base}_{family_id}"

        # 1. Быстрая проверка в кэше сессии
        if specific_cache_key in self.context_cache:
            return

        # 2. Проверка в БД (через глобальный хеш)
        # Хеш для БД: md5(family_id + context_hash)
        unique_db_hash = compute_unique_clan_hash(family_id, context_hash_base)

        # Этот метод должен быть быстрым (SELECT id FROM clans WHERE unique_hash = ...)
        # Мы проверяем: есть ли уже "Бандиты для Руин Т1"?
        existing_clan = await self.repo.get_clan_by_unique_hash(unique_db_hash)

        if existing_clan:
            # Уже есть в базе -> кладем в кэш и идем дальше
            self.context_cache[specific_cache_key] = existing_clan
            return

        # 3. Если нет ни в кэше, ни в БД -> ГЕНЕРИРУЕМ
        # Это произойдет только 1 раз для каждого типа врага в регионе
        clan = await self._process_family_guarded(
            family_id=family_id,
            tier=tier,
            clean_tags=clean_tags,
            context_hash=context_hash_base,
            unique_hash=unique_db_hash,
            zone_id=zone_id,
        )

        if clan:
            self.context_cache[specific_cache_key] = clan

    async def _process_family_guarded(self, *args: Any, **kwargs: Any) -> GeneratedClanORM | None:
        async with self._llm_semaphore:
            return await self._process_single_family(*args, **kwargs)

    async def _process_single_family(
        self, family_id: str, tier: int, clean_tags: list[str], context_hash: str, unique_hash: str, zone_id: str
    ) -> GeneratedClanORM | None:
        family_config: MonsterFamilyDTO | None = get_family_config(family_id)
        if not family_config:
            return None

        valid_unit_ids: list[str] = get_available_variants_for_tier(family_id, tier)
        if not valid_unit_ids:
            return None

        try:
            log.info(f"ClanFactory | Generating NEW Pool | family='{family_id}' context='{context_hash[:8]}'")
            return await self._create_new_population(
                family_config, valid_unit_ids, tier, clean_tags, context_hash, unique_hash, zone_id
            )
        except OSError as e:
            log.exception(f"ProcessFamilyError | family='{family_id}' error='{e}'")
            return None

    async def _create_new_population(
        self,
        config: MonsterFamilyDTO,
        units: list[str],
        tier: int,
        tags: list[str],
        ctx_hash: str,
        uniq_hash: str,
        zone_id: str,
    ) -> GeneratedClanORM:
        flavor_data = await self._generate_flavor_with_llm(config, units, tier, tags)
        new_clan = self._build_clan_orm(config, tier, tags, ctx_hash, uniq_hash, flavor_data, zone_id)
        monsters = self._build_monster_list(new_clan, config, units, tier, flavor_data)
        return await self.repo.create_clan_with_members(new_clan, monsters)

    async def _generate_flavor_with_llm(
        self, config: MonsterFamilyDTO, units: list[str], tier: int, tags: list[str]
    ) -> dict:
        units_with_roles = {
            unit_id: f"[{config.variants[unit_id].role.title()}] {config.variants[unit_id].narrative_hint}"
            for unit_id in units
        }
        prompt_data = {
            "family_id": config.id,
            "archetype": config.archetype,
            "organization": config.organization_type,
            "family_tags": config.default_tags,
            "context_tags": tags,
            "tier": tier,
            "units_to_name": units_with_roles,
        }
        user_text = json.dumps(prompt_data, ensure_ascii=False)
        try:
            raw_resp = await gemini_answer(mode="clan_generation", user_text=user_text)
            clean_json = raw_resp.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except json.JSONDecodeError as e:
            log.error(f"LLMError | family='{config.id}' error='{e}'")
            return {}

    def _build_clan_orm(
        self,
        config: MonsterFamilyDTO,
        tier: int,
        tags: list[str],
        ctx_hash: str,
        uniq_hash: str,
        flavor: dict,
        zone_id: str,
    ) -> GeneratedClanORM:
        clan_name = flavor.get("name_ru", f"Группа {config.id}")
        return GeneratedClanORM(
            id=uuid4(),
            family_id=config.id,
            tier=tier,
            zone_id=zone_id,  # Просто маркер происхождения, не влияет на логику
            context_hash=ctx_hash,
            unique_hash=uniq_hash,
            raw_tags=tags,
            flavor_content=flavor,
            name_ru=clan_name,
            description=flavor.get("description", "Обитатели этих мест."),
        )

    def _build_monster_list(
        self, clan: GeneratedClanORM, config: MonsterFamilyDTO, units: list[str], tier: int, flavor: dict
    ) -> list[GeneratedMonsterORM]:
        monsters = []
        scaling = TIER_SCALING_CONFIG.get(tier, {"stat_mult": 1.0})
        multiplier = scaling["stat_mult"]
        for unit_key in units:
            variant_dto: MonsterVariantDTO = config.variants[unit_key]
            unit_flavor = flavor.get("variants_flavor", {}).get(unit_key, {})
            name = unit_flavor.get("name", f"{variant_dto.role.title()} {unit_key}")
            base_stats = variant_dto.base_stats.model_dump()
            scaled_stats = {k: int(v * multiplier) for k, v in base_stats.items()}
            loadout_data = variant_dto.fixed_loadout.model_dump(exclude_none=True)
            monster = GeneratedMonsterORM(
                id=uuid4(),
                clan_id=clan.id,
                variant_key=unit_key,
                role=variant_dto.role,
                threat_rating=variant_dto.cost,
                name_ru=name,
                description=json.dumps(unit_flavor.get("flavor", {}), ensure_ascii=False),
                scaled_base_stats=scaled_stats,
                loadout_ids=loadout_data,
                skills_snapshot=variant_dto.skills,
            )
            monsters.append(monster)
        return monsters

    def _select_candidates(self, tier: int, biome_id: str) -> set[str]:
        in_biome = BIOME_FAMILIES.get(biome_id, set())
        in_tier = TIER_AVAILABILITY.get(tier, set())
        if "all_families" in in_tier:
            return in_biome
        return in_biome & in_tier

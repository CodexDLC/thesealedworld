import json
from dataclasses import dataclass
from typing import Any

from loguru import logger as log

from src.backend.features.character.runtime import CharacterVitalsCalculator
from src.backend.features.character.runtime.combat_actor_input import CharacterCombatActorInputBuilder
from src.backend.features.character.runtime.combat_math_model import CharacterCombatMathModelBuilder
from src.backend.features.character.schemas.session import CharacterSessionAttributesDTO
from src.backend.features.combat.dto.actor import ActorMetaDTO, ActorRawDTO
from src.backend.features.combat.dto.ids import normalize_actor_id
from src.backend.features.combat.integrations import CombatSessionIntegration
from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.runtime.generation_fields import build_scaled_skills

ANCHOR_FAMILY_ID = "anchor_sovereigns"
ANCHOR_FORCE_TEAM = "anchor_force"


@dataclass(frozen=True)
class AnchorProjectionConfig:
    actor_id: int
    variant_id: str
    name: str
    battle_types: tuple[str, ...]
    arrival_text: str


ANCHOR_PROJECTIONS: dict[str, AnchorProjectionConfig] = {
    "north_stasis": AnchorProjectionConfig(
        actor_id=-701,
        variant_id="north_stasis_sovereign",
        name="Проекция Северного Стазиса",
        battle_types=("shadow", "duel"),
        arrival_text="Северный Стазис замечает остановившийся бой. Воздух густеет, и его проекция входит в круг.",
    ),
    "south_entropy": AnchorProjectionConfig(
        actor_id=-702,
        variant_id="south_entropy_sovereign",
        name="Проекция Южной Энтропии",
        battle_types=("rift", "standard"),
        arrival_text="Южная Энтропия принимает затянувшееся молчание за приглашение. На поле осыпается пепел.",
    ),
    "west_gravity": AnchorProjectionConfig(
        actor_id=-703,
        variant_id="west_gravity_sovereign",
        name="Проекция Западной Гравитации",
        battle_types=("arena", "pvp"),
        arrival_text="Западная Гравитация склоняет арену. Те, кто не сделал выбор, теперь падают к ее воле.",
    ),
    "east_evolution": AnchorProjectionConfig(
        actor_id=-704,
        variant_id="east_evolution_sovereign",
        name="Проекция Восточной Эволюции",
        battle_types=("pve", "field"),
        arrival_text="Восточная Эволюция не терпит застоя. Живая проекция прорастает в бой и ищет слабые формы.",
    ),
}


class ChaosService:
    """
    Сервис вмешательства высших сил. Отвечает за призыв анкорной проекции
    в затянувшийся бой.
    """

    FORCE_TEAM = ANCHOR_FORCE_TEAM

    def __init__(self, combat_sessions: CombatSessionIntegration, anchor_snapshots: Any | None = None):
        self.combat_sessions = combat_sessions
        self.anchor_snapshots = anchor_snapshots

    async def spawn_cleaner(self, session_id: str) -> bool:
        """
        Призывает проекцию одного из четырех Якорей в бой.
        Возвращает True, если успешно призван.
        """
        # 1. Проверяем, есть ли он уже
        meta_raw = await self.combat_sessions.get_raw_meta(session_id)
        if not meta_raw:
            return False

        # Проверка через actors_info (быстрее, чем парсить teams)
        actors_info = json.loads(meta_raw.get("actors_info") or "{}")
        if any(str(config.actor_id) in actors_info for config in ANCHOR_PROJECTIONS.values()):
            return False  # Уже здесь

        projection = self._select_projection(session_id, meta_raw)
        log.warning(
            "AnchorIntervention | session_id={} projection={} variant={}",
            session_id,
            projection.name,
            projection.variant_id,
        )

        # 2. Создаем actor document из monster family resource
        projection_data = await self._create_projection_data(
            projection,
            battle_type=str(meta_raw.get("battle_type") or "standard"),
        )

        # 3. Вызываем универсальный метод менеджера
        await self.combat_sessions.hot_join_actor(
            session_id=session_id,
            actor_id=projection.actor_id,
            team_name=self.FORCE_TEAM,
            actor_data=projection_data,
            is_ai=True,
        )

        # 4. Лог
        await self.combat_sessions.add_log(
            session_id,
            projection.arrival_text,
            tags=["anchor", "higher_force", "spawn", projection.variant_id],
        )

        return True

    def _select_projection(self, session_id: str, meta_raw: dict[str, Any]) -> AnchorProjectionConfig:
        battle_type = str(meta_raw.get("battle_type") or "standard")
        for projection in ANCHOR_PROJECTIONS.values():
            if battle_type in projection.battle_types:
                return projection

        projections = tuple(ANCHOR_PROJECTIONS.values())
        index = sum(ord(char) for char in session_id) % len(projections)
        return projections[index]

    async def _create_projection_data(self, projection: AnchorProjectionConfig, *, battle_type: str) -> dict[str, Any]:
        """Генерирует actor document проекции из monster family resource."""
        if self.anchor_snapshots is not None:
            snapshot = await self.anchor_snapshots.get_snapshot(projection.variant_id)
            if snapshot is not None:
                return CombatLifecycleService(store=self.combat_sessions)._build_actor_doc(
                    str(projection.actor_id),
                    self.FORCE_TEAM,
                    snapshot,
                    battle_type=battle_type,
                )
            log.error("AnchorIntervention | missing_cached_snapshot variant_id={}", projection.variant_id)

        family = get_family_config(ANCHOR_FAMILY_ID)
        if family is None:
            log.error("AnchorIntervention | missing_family family_id={}", ANCHOR_FAMILY_ID)
            return self._create_fallback_projection_data(projection)

        variant = family.variants.get(projection.variant_id)
        if variant is None:
            log.error("AnchorIntervention | missing_variant variant_id={}", projection.variant_id)
            return self._create_fallback_projection_data(projection)

        attributes = variant.base_stats.model_dump(mode="json")
        skills = build_scaled_skills(family, variant).skills
        vitals = CharacterVitalsCalculator.build_initial_vitals(
            CharacterSessionAttributesDTO.model_validate(attributes)
        ).model_dump(mode="json")
        hp = int((vitals.get("hp") or {}).get("cur") or 1)
        max_hp = int((vitals.get("hp") or {}).get("max") or hp)
        energy = int((vitals.get("energy") or {}).get("cur") or 1)
        max_energy = int((vitals.get("energy") or {}).get("max") or energy)
        items = {"layout": {"equipment": {}, "belt": {}}, "by_id": {}}
        raw = CharacterCombatMathModelBuilder().build_raw(attributes=attributes, items=items, skills=skills)
        raw["tags"] = sorted(set(["monster", variant.role, family.id, family.archetype, *family.default_tags]))
        loadout = CharacterCombatActorInputBuilder._loadout(items, skills)

        meta = ActorMetaDTO(
            id=normalize_actor_id(projection.actor_id),
            name=projection.name,
            type="ai",
            team=self.FORCE_TEAM,
            template_id=variant.id,
            is_ai=True,
            archetype=family.archetype,
            hp=hp,
            max_hp=max_hp,
            en=energy,
            max_en=max_energy,
            tactics=100,
            afk_level=0,
            is_dead=False,
            tokens={},
        )

        return {
            "meta": meta.model_dump(mode="json"),
            "raw": raw,
            "skills": skills,
            "loadout": loadout,
            "statuses": {"abilities": [], "effects": []},
            "xp_buffer": {},
            "metrics": {},
            "explanation": {},
            "source": {
                "family_id": ANCHOR_FAMILY_ID,
                "variant_id": variant.id,
                "projection": True,
                "narrative_hint": variant.narrative_hint,
            },
        }

    def _create_fallback_projection_data(self, projection: AnchorProjectionConfig) -> dict[str, Any]:
        meta = ActorMetaDTO(
            id=normalize_actor_id(projection.actor_id),
            name=projection.name,
            type="ai",
            team=self.FORCE_TEAM,
            template_id=projection.variant_id,
            is_ai=True,
            hp=2500,
            max_hp=2500,
            en=1000,
            max_en=1000,
            tactics=100,
        )
        raw = ActorRawDTO(
            attributes={
                "strength": {"base": 200, "source": {}, "temp": {}},
                "endurance": {"base": 200, "source": {}, "temp": {}},
                "agility": {"base": 120, "source": {}, "temp": {}},
                "mental": {"base": 200, "source": {}, "temp": {}},
            },
            modifiers={"main_hand_damage_base": {"base": 100, "source": {}, "temp": {}}},
        )
        return {
            "meta": meta.model_dump(mode="json"),
            "raw": raw.model_dump(mode="json"),
            "skills": {"skill_unarmed": 1.0, "skill_tactics": 1.0},
            "loadout": {"layout": {"main_hand": "skill_unarmed"}, "known_abilities": []},
            "statuses": {"abilities": [], "effects": []},
            "xp_buffer": {},
            "metrics": {},
            "explanation": {},
        }

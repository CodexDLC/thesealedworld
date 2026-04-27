from src.backend.resources.game_data.common.targeting import TargetType
from src.backend.resources.game_data.feints.schemas import FeintConfigDTO, FeintCostDTO

DIRTY_FEINTS = [
    # --- SAND THROW (Бросок песка) ---
    FeintConfigDTO(
        feint_id="sand_throw",
        name_ru="Бросок песка",
        description_ru="Ослепляет противника, снижая его точность.",
        cost=FeintCostDTO(tactics={"tempo": 3}),
        target=TargetType.SINGLE_ENEMY,
        raw_mutations={"physical_damage_mult": "-0.8"},  # Почти нет урона
        effects=[{"id": "blind", "params": {"duration": 2}}],
    ),
    # --- LOW BLOW (Удар ниже пояса) ---
    FeintConfigDTO(
        feint_id="low_blow",
        name_ru="Подлый удар",
        description_ru="Болезненный удар, который может оглушить.",
        cost=FeintCostDTO(tactics={"crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["control.stun_on_hit"],
    ),
]

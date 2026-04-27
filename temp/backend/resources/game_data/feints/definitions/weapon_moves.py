from src.backend.resources.game_data.common.targeting import TargetType
from src.backend.resources.game_data.feints.schemas import FeintConfigDTO, FeintCostDTO

WEAPON_FEINTS = [
    # --- PIERCING THRUST (Пронзающий выпад) - Копья/Кинжалы ---
    FeintConfigDTO(
        feint_id="piercing_thrust",
        name_ru="Пронзающий выпад",
        description_ru="Игнорирует броню цели.",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations={"formula.can_pierce": True},
    ),
    # --- SHIELD BASH (Удар щитом) ---
    FeintConfigDTO(
        feint_id="shield_bash",
        name_ru="Удар щитом",
        description_ru="Наносит урон и оглушает. Требует щит.",
        cost=FeintCostDTO(tactics={"block": 2}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["control.stun_on_hit"],
    ),
    # --- CLEAVE (Рассечение) - Топоры/Мечи ---
    FeintConfigDTO(
        feint_id="cleave",
        name_ru="Рассечение",
        description_ru="Атакует несколько целей перед собой.",
        cost=FeintCostDTO(tactics={"hit": 2, "crit": 1}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        raw_mutations={"physical_damage_mult": "-0.3"},
    ),
]

from src.backend.resources.game_data.common.targeting import TargetType
from src.backend.resources.game_data.feints.schemas import FeintConfigDTO, FeintCostDTO

TACTICAL_FEINTS = [
    # --- TRUE STRIKE (Верный удар) ---
    FeintConfigDTO(
        feint_id="true_strike",
        name_ru="Верный удар",
        description_ru="Игнорирует уклонение противника, но наносит меньше урона.",
        cost=FeintCostDTO(tactics={"hit": 2}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["accuracy.true_strike"],
        raw_mutations={"physical_damage_mult": "-0.2"},  # Снижение на 20%
    ),
    # --- POWER ATTACK (Сильный удар) ---
    FeintConfigDTO(
        feint_id="power_attack",
        name_ru="Сильный удар",
        description_ru="Наносит повышенный урон, но снижает точность.",
        cost=FeintCostDTO(tactics={"crit": 1, "hit": 1}),
        target=TargetType.SINGLE_ENEMY,
        raw_mutations={
            "physical_damage_mult": "+0.5",  # Бонус +50%
            "accuracy_mult": "-0.2",  # Штраф -20%
        },
    ),
    # --- DEFENSIVE STANCE (Осторожный удар) ---
    FeintConfigDTO(
        feint_id="defensive_strike",
        name_ru="Осторожный удар",
        description_ru="Удар с подготовкой к защите. Повышает шанс контратаки при уклонении.",
        cost=FeintCostDTO(tactics={"tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["dodge.counter_on_dodge"],
    ),
]

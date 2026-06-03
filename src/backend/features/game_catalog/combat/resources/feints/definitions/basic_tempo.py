from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatDescriptionDTO,
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

_BASIC_TEMPO_TAGS = ["basic", "tempo", "preparation", "counter", "reactive"]


BASIC_TEMPO_FEINTS_TECHNICAL = {
    "basic_seize_tempo": FeintTechnicalDTO(
        feint_id="basic_seize_tempo",
        cost=FeintCostDTO(tactics={"tempo": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_BASIC_TEMPO_TAGS, "tier_1"],
        purchase_group="basic",
        preparation_effects=[
            {"id": "prep_counter_on_parry", "target_actor": "source"},
        ],
    ),
}

_BASIC_TEMPO_TEXTS = {
    "basic_seize_tempo": (
        "Перехват темпа",
        "взяв темп размена раскрыть окно контратаки на парирование",
        "Базовый темповой финт: следующее успешное парирование гарантирует контратаку.",
        "взяв темп размена",
        "и закрепляет темповое преимущество",
        "и удерживает темп размена на грани контратаки",
    ),
}


def _basic_tempo_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _BASIC_TEMPO_TEXTS[feint_id]
    return build_combat_description(
        resource_type="feints",
        resource_id=feint_id,
        icon=f"combat/feints/{feint_id}.svg",
        display_name=display_name,
        ui_label=ui_label,
        short_description=short,
        humanoid_long_description=short,
        humanoid_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но сохраняет темповое окно для ответа"],
            dodge=["но {target} уходит с линии"],
            parry=["но {target} сбивает атаку"],
            block=["но {target} принимает удар на защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но сохраняет темповое окно для ответа"],
            dodge=["но {target} выходит из линии"],
            parry=["но {target} сбивает атаку движением"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


BASIC_TEMPO_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_basic_tempo_description(feint_id),
    )
    for feint_id, technical in BASIC_TEMPO_FEINTS_TECHNICAL.items()
}

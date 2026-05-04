from src.backend.resources.game_data.triggers.schemas import TriggerDTO

ON_BLOCK_RULES = [
    # --- ON_BLOCK (Успех) ---
    TriggerDTO(
        id="shield_bash_on_block",
        name_ru="Удар щитом (Блок)",
        description_ru="Успешный блок наносит ответный удар щитом.",
        event="ON_BLOCK",
        chance=1.0,
        mutations={
            "chain_events.trigger_extra_strike": True,  # Или спец. флаг shield_bash
        },
    ),
]

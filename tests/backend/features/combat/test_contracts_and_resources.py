from src.backend.features.combat.dto import (
    BattleContext,
    BattleMeta,
    CombatActionDTO,
    CombatMoveDTO,
    ExchangePayload,
)
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.game_catalog.combat.resources import CombatResourceCatalogService
from src.backend.features.game_catalog.combat.resources.abilities import get_ability_config
from src.backend.features.game_catalog.combat.resources.feints import get_feint_catalog_entry, get_feint_config


def test_combat_action_contract_preserves_exchange_pair() -> None:
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="true_strike"),
    )
    partner = CombatMoveDTO(move_id="m2", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1))

    action = CombatActionDTO(action_type="exchange", move=move, partner_move=partner)

    assert action.move.payload.target_id == 2
    assert action.partner_move is not None
    assert action.partner_move.payload.target_id == 1
    assert action.is_forced is False


def test_battle_context_contract_has_target_return_queue() -> None:
    meta = BattleMeta(
        active=1,
        step_counter=0,
        active_actors_count=0,
        teams={"a": [], "b": []},
        battle_type="standard",
        location_id="test",
    )
    context = BattleContext(session_id="combat-1", meta=meta, actors={})

    context.pending_target_returns.append({"actor_id": 1, "target_id": 2})

    assert context.pending_target_returns == [{"actor_id": 1, "target_id": 2}]


def test_combat_resources_load_runtime_and_public_catalog() -> None:
    catalog = CombatResourceCatalogService.load_default().all_public_text()

    assert get_ability_config("fireball") is not None
    assert get_feint_config("true_strike") is not None
    assert catalog["abilities"]["fireball"]["target"] == "single_enemy"
    assert catalog["feints"]["shield_bash"]["title"] == "Удар щитом"
    assert catalog["triggers"]["bleed_on_crit"]["event"] == "ON_CRIT"


def test_feint_catalog_entry_splits_technical_and_taxonomy_descriptions() -> None:
    entry = get_feint_catalog_entry("cleave")

    assert entry is not None
    assert entry.key == "combat.feint.cleave"
    assert entry.technical.feint_id == "cleave"
    assert entry.technical.target_count == 3
    assert entry.descriptive.default_taxonomy == "humanoid"
    assert set(entry.descriptive.variants) == {"humanoid", "beast"}
    assert entry.descriptive.variants["humanoid"].icon == "combat/feints/cleave.png"
    assert entry.descriptive.variants["beast"].display_name == "Рассечение"
    assert len(entry.descriptive.variants["humanoid"].event_texts.hit) >= 2
    assert len(entry.descriptive.variants["beast"].event_texts.dodge) >= 2
    assert "{source}" in entry.descriptive.variants["humanoid"].event_texts.hit[0]
    assert "{target}" in entry.descriptive.variants["beast"].event_texts.hit[0]


def test_combat_runtime_can_resolve_catalog_entry_by_stable_key() -> None:
    entry = CombatCatalogIntegrator.get_catalog_entry_by_key("combat.feint.cleave")

    assert entry is not None
    assert entry.technical.feint_id == "cleave"
    assert entry.descriptive.variants["beast"].event_texts.hit

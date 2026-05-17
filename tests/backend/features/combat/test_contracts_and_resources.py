from src.backend.features.combat.dto import (
    BattleContext,
    BattleMeta,
    CombatActionDTO,
    CombatMoveDTO,
    ExchangePayload,
)
from src.backend.features.combat.dto.pipeline import PipelineContextDTO
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.engine.pipeline_mutation_service import PipelineMutationService
from src.backend.features.game_catalog.combat.resources import CombatResourceCatalogService
from src.backend.features.game_catalog.combat.resources.abilities import get_ability_catalog_entry
from src.backend.features.game_catalog.combat.resources.common import CombatEventTextSetDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import (
    PIPELINE_MUTATION_CONTRACTS,
    pipeline_mutation,
)
from src.backend.features.game_catalog.combat.resources.feints import get_feint_catalog_entry
from src.backend.features.game_catalog.combat.resources.gifts import get_gift_catalog_entry
from src.backend.features.game_catalog.combat.resources.items import get_combat_item_action_catalog_entry
from src.shared.schemas.messages import GameMessageDTO, GameMessageTabDTO, GameMessageTemplateDTO


def test_combat_action_contract_preserves_exchange_pair() -> None:
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="true_strike"),
    )
    partner = CombatMoveDTO(move_id="m2", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1))

    action = CombatActionDTO(action_type="exchange", move=move, partner_move=partner)

    assert action.move.payload.target_id == "2"
    assert action.partner_move is not None
    assert action.partner_move.payload.target_id == "1"
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

    context.pending_target_returns.append({"source_id": "1", "target_id": "2"})

    assert context.pending_target_returns == [{"source_id": "1", "target_id": "2"}]


def test_combat_resources_load_runtime_and_public_catalog() -> None:
    catalog = CombatResourceCatalogService.load_default().all_public_text()

    assert get_ability_catalog_entry("fireball") is not None
    assert get_feint_catalog_entry("true_strike") is not None
    assert catalog["abilities"]["fireball"]["target"] == "single_enemy"
    assert catalog["combat_entries"]["combat.ability.fireball"]["resource_id"] == "fireball"
    assert catalog["combat_entries"]["combat.gift.gift_true_fire"]["resource_id"] == "gift_true_fire"
    assert catalog["combat_entries"]["combat.item.fire_grenade"]["resource_id"] == "fire_grenade"
    assert catalog["feints"]["shield_bash"]["title"] == "Удар щитом"
    assert not any(key.startswith("combat.trigger.crit.") for key in catalog["triggers"])
    assert not any(key.startswith("combat.trigger.crit.") for key in catalog["combat_entries"])
    assert catalog["triggers"]["combat.trigger.weapon.heavy_crit"]["resource_id"] == "weapon_heavy_crit"
    assert catalog["combat_entries"]["combat.trigger.weapon.heavy_crit"]["resource_id"] == "weapon_heavy_crit"
    assert catalog["combat_entries"]["combat.basic_exchange.skill_swords.main_hand"]["resource_id"] == (
        "skill_swords.main_hand"
    )


def test_ability_gift_and_item_catalog_entries_split_technical_and_descriptive() -> None:
    ability = get_ability_catalog_entry("fireball")
    gift = get_gift_catalog_entry("gift_true_fire")
    item = get_combat_item_action_catalog_entry("fire_grenade")

    assert ability is not None
    assert ability.key == "combat.ability.fireball"
    assert ability.technical.ability_id == "fireball"
    assert not hasattr(ability.technical, "name_ru")
    assert ability.descriptive.variants["humanoid"].event_texts.area_result
    assert ability.descriptive.variants["humanoid"].event_texts.no_resource

    assert gift is not None
    assert gift.key == "combat.gift.gift_true_fire"
    assert gift.technical.gift_id == "gift_true_fire"
    assert gift.technical.abilities == ["fireball", "flame_thrower"]
    assert not hasattr(gift.technical, "description")
    assert gift.descriptive.variants["humanoid"].display_name == "Истинное Пламя"

    assert item is not None
    assert item.key == "combat.item.fire_grenade"
    assert item.technical.ability_id == "fireball"
    assert item.descriptive.variants["humanoid"].event_texts.area_result


def test_feint_catalog_entry_splits_technical_and_taxonomy_descriptions() -> None:
    entry = get_feint_catalog_entry("cleave")

    assert entry is not None
    assert entry.key == "combat.feint.cleave"
    assert entry.technical.feint_id == "cleave"
    assert entry.technical.target_count == 3
    assert entry.descriptive.default_taxonomy == "humanoid"
    assert set(entry.descriptive.variants) == {"humanoid", "beast"}
    assert entry.descriptive.variants["humanoid"].icon == "combat/feints/cleave.svg"
    assert entry.descriptive.variants["beast"].display_name == "Рассечение"
    assert len(entry.descriptive.variants["humanoid"].event_texts.hit) >= 2
    assert len(entry.descriptive.variants["beast"].event_texts.dodge) >= 2
    assert "{source}" in entry.descriptive.variants["humanoid"].event_texts.use[0]
    assert "{target}" in entry.descriptive.variants["beast"].event_texts.hit[0]


def test_combat_runtime_can_resolve_catalog_entry_by_stable_key() -> None:
    entry = CombatCatalogIntegrator.get_catalog_entry_by_key("combat.feint.cleave")

    assert entry is not None
    assert entry.technical.feint_id == "cleave"
    assert entry.descriptive.variants["beast"].event_texts.hit

    ability_entry = CombatCatalogIntegrator.get_catalog_entry_by_key("combat.ability.fireball")
    assert ability_entry is not None
    assert ability_entry.technical.ability_id == "fireball"


def test_combat_description_resolves_event_and_exchange_templates_without_formatting() -> None:
    entry = get_feint_catalog_entry("cleave")

    assert entry is not None

    resolved = entry.descriptive.resolve_exchange_template("hit", taxonomy_chain=["beast.wolves", "beast"])

    assert resolved is not None
    assert resolved.event == "hit"
    assert resolved.taxonomy == "beast"
    assert resolved.variant == 0
    assert "{source}" in resolved.text
    assert "{target}" in resolved.text

    trigger = CombatCatalogIntegrator.get_trigger_catalog_entry("weapon_serrated_bleed_crit")
    assert trigger is not None
    proc = trigger.descriptive.resolve_event_template("crit_proc", taxonomy_chain=["humanoid"])

    assert proc is not None
    assert proc.event == "crit_proc"
    assert proc.taxonomy == "humanoid"
    assert "{source}" in proc.text


def test_combat_event_text_set_prefers_semantic_exchange_parts() -> None:
    texts = CombatEventTextSetDTO(
        attack_use=["{source} attacks {target}"],
        hit_result=["dealing {damage} damage"],
        use=["legacy use"],
        hit=["legacy hit"],
    )

    assert texts.event_template("hit") == "legacy hit"
    assert texts.exchange_template("hit") == "{source} attacks {target}, dealing {damage} damage."


def test_pipeline_mutation_contracts_are_technical_and_apply_to_context() -> None:
    assert "chain.trigger_cleave" not in PIPELINE_MUTATION_CONTRACTS
    assert PIPELINE_MUTATION_CONTRACTS["ignore_miss"].path == "flags.force.hit"
    assert PIPELINE_MUTATION_CONTRACTS["ignore_evasion"].path == "flags.force.hit_evasion"

    ctx = PipelineContextDTO()

    PipelineMutationService.apply(
        applications=[
            pipeline_mutation("ignore_evasion"),
            pipeline_mutation("roll_flat_armor_ignore"),
            pipeline_mutation("flat_armor_ignore_chance_bonus", 0.5),
            pipeline_mutation("boost_flat_armor_penetration"),
            pipeline_mutation("flat_armor_penetration_bonus_pct", 0.5),
            pipeline_mutation("stage.check_parry", False),
            pipeline_mutation("weapon_effect_value", 2.0),
            pipeline_mutation("chain.preserve_feint"),
        ],
        ctx=ctx,
        source="feint",
    )

    assert ctx.flags.force.hit_evasion is True
    assert ctx.flags.formula.roll_flat_armor_ignore is True
    assert ctx.mods.flat_armor_ignore_chance_bonus == 0.5
    assert ctx.flags.formula.boost_flat_armor_penetration is True
    assert ctx.mods.flat_armor_penetration_bonus_pct == 0.5
    assert ctx.stages.check_parry is False
    assert ctx.mods.weapon_effect_value == 2.0
    assert ctx.result.chain_events.preserve_feint is True


def test_weapon_technique_feint_resolves_weapon_render_context() -> None:
    entry = get_feint_catalog_entry("measured_strike")

    assert entry is not None
    assert entry.technical.cost.tactics == {"hit": 3}
    assert entry.technical.hit_damage_bonus_per_tier == 3
    assert [application.mutation_id for application in entry.technical.pipeline_mutations] == ["ignore_miss"]

    context = CombatCatalogIntegrator.get_feint_render_context(
        "measured_strike",
        skill_key="skill_swords",
        outcome="hit",
        seed="stable",
        bonus_damage=6,
    )

    assert context is not None
    assert "{weapon_attack_form}" in context.template
    assert context.variables["bonus_damage"] == 6
    assert context.variables["weapon_attack_form"]


def test_trigger_rules_use_pipeline_mutation_applications_not_raw_paths() -> None:
    rule = CombatCatalogIntegrator.get_trigger_rule("weapon_heavy_crit")

    assert rule is not None
    assert "mutations" not in rule
    assert [application.mutation_id for application in rule["pipeline_mutations"]] == [
        "crit_damage_boost",
        "weapon_effect_value",
        "boost_flat_armor_penetration",
        "flat_armor_penetration_bonus_pct",
    ]


def test_weapon_armor_triggers_target_flat_armor_layers() -> None:
    gap = CombatCatalogIntegrator.get_trigger_rule("weapon_flat_armor_gap_crit")
    bypass = CombatCatalogIntegrator.get_trigger_rule("weapon_flat_armor_bypass_crit")
    crush = CombatCatalogIntegrator.get_trigger_rule("weapon_flat_armor_crush_crit")

    assert gap is not None
    assert [application.mutation_id for application in gap["pipeline_mutations"]] == [
        "roll_flat_armor_ignore",
        "flat_armor_ignore_chance_bonus",
    ]
    assert gap["pipeline_mutations"][1].value_override == 0.5

    assert bypass is not None
    assert [application.mutation_id for application in bypass["pipeline_mutations"]] == ["ignore_flat_armor"]

    assert crush is not None
    assert [application.mutation_id for application in crush["pipeline_mutations"]] == [
        "boost_flat_armor_penetration",
        "flat_armor_penetration_bonus_pct",
    ]
    assert crush["pipeline_mutations"][1].value_override == 0.5


def test_game_message_contract_wraps_template_variables_and_result() -> None:
    message = GameMessageDTO(
        channel="combat",
        tab=GameMessageTabDTO(
            kind="combat",
            key="combat_combat-1",
            title="БОЙ",
            open_policy="force_open",
            closeable=True,
            accent="combat",
        ),
        scope="combat_session",
        scope_id="combat-1",
        recipients=["1", "2"],
        template=GameMessageTemplateDTO(
            key="combat.basic_exchange.skill_swords.main_hand",
            event="hit",
            taxonomy="humanoid",
            text="{source} strikes {target}.",
        ),
        variables={"source": {"id": "1", "label": "A"}, "target": {"id": "2", "label": "B"}},
        result={"resources": [{"actor_id": "2", "resource": "hp", "delta": -4}]},
        presentation={"render": "combat_inline_result", "severity": "normal"},
    )

    assert message.channel == "combat"
    assert message.tab is not None
    assert message.tab.open_policy == "force_open"
    assert message.template.text == "{source} strikes {target}."
    assert message.variables["source"]["label"] == "A"
    assert message.result["resources"][0]["delta"] == -4
    assert message.presentation.render == "combat_inline_result"

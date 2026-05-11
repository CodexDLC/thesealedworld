from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.frontend.game_features.combat.view_models.screen import (
    build_combat_result_screen_vm,
    build_combat_screen_from_result_vm,
    build_combat_screen_vm,
)
from src.shared.schemas.combat import (
    CombatActorCardDTO,
    CombatActorVitalsDTO,
    CombatDashboardDTO,
    CombatDeltaDTO,
    CombatEffectBadgeDTO,
    CombatEventDTO,
    CombatFeintOptionDTO,
    CombatLogTurnDTO,
    CombatResultActionDTO,
    CombatResultDTO,
)


def test_combat_shell_forces_three_zone_layout():
    template = Path("src/frontend/templates/game/session_content_inner.html").read_text()

    assert "combat_layout = domain == 'combats'" in template
    assert "combat_sidebars = combat_layout" in template
    assert "shell_left_open" in template
    assert "'combat-layout' if combat_layout else ''" in template
    assert "combat_sidebars or (not combat_layout and session_ui and session_ui.left_open)" in template
    assert "combat_sidebars or (not combat_layout and session_ui and session_ui.right_open)" in template


def test_combat_viewport_uses_team_bars_and_command_deck():
    template = Path("src/frontend/templates/game/domains/combat/viewport/main.html").read_text()

    assert "combat-viewport" in template
    assert "combat-screen-shell" in template
    assert "combat-battle-header" in template
    assert "combat-team-bars" in template
    assert "combat_screen.session_id" in template
    assert "QUEUE" in template
    assert "LOCKED" in template
    assert "combat-stage" not in template
    assert "combat-duelist--hero" not in template
    assert "combat-duelist--target" not in template
    assert "combat-command-deck" in template
    assert 'hx-trigger="every 2s"' not in template
    assert 'hx-trigger="load delay:1500ms"' in template
    assert "combat_screen.action_state == 'ACTION_LOCKED'" in template
    assert 'hx-disabled-elt="this"' in template
    assert "ACTION_LOCKED" in template
    assert "REFRESH_TARGET" in template
    assert "combat-action-topline" in template
    assert "combat-token-strip" in template
    assert 'data-catalog="{{ token.catalog }}"' in template
    assert 'data-catalog-tooltip="description"' in template
    assert "combat_screen.feint_options[:3]" in template
    assert "combat-feint-row" in template
    assert 'hx-post="/game/combat/feint-pin"' in template
    assert "action.pinned" in template
    assert 'data-catalog="{{ action.catalog }}"' in template
    assert 'data-catalog-field="label"' in template
    assert 'data-catalog-field="title"' not in template
    assert "action.cost_items" in template
    assert "combat-feint-cost" in template
    assert "combat_screen.ability_options" in template
    assert "ability_source is mapping" in template
    assert "ability_source is sequence" in template
    assert "combat-ability-option" in template
    assert "ability-debug-swirl.svg" not in template
    assert "DEBUG_ABILITY_PLACEHOLDER" not in template
    assert 'include "game/domains/combat/viewport/log_panel.html"' not in template
    assert "combat-log-panel" not in template
    assert "combat_result" in template
    assert "combat-result-hero" in template
    assert "combat-result-field" in template
    assert "combat-result-report" in template
    assert "combat-result-rewards" in template
    assert "ПОЛУЧЕНО ОПЫТА ВСЕГО" in template
    assert "НАВЫКИ НЕ ИЗМЕНИЛИСЬ" in template
    assert "result_primary_state" in template
    assert "combat_result_screen is defined" in template
    assert "OUTCOME" not in template
    assert "ARCHIVE" not in template
    assert "combat-wait-scene" in template
    assert "ds-panel combat-summary" not in template
    wait_scene_block = template.split("combat-wait-scene", maxsplit=1)[1].split("{% endif %}", maxsplit=1)[0]
    assert "TARGET_QUEUE_EMPTY" not in wait_scene_block


def test_combat_sidebars_use_combat_panels():
    left = Path("src/frontend/templates/game/domains/combat/left_sidebar/main.html").read_text()
    right = Path("src/frontend/templates/game/domains/combat/right_sidebar/main.html").read_text()

    assert "combat-panel combat-actor-panel" in left
    assert "combat-panel combat-actor-panel" in right
    assert "combat-panel-header" in left
    assert "combat-panel-header" in right
    assert "combat-target-empty-panel" in right
    assert "TARGET_QUEUE_EMPTY" in right
    assert "Цель не найдена" in right
    assert "combat_result" in left
    assert "FINAL PLAYER STATE" in left
    assert "FINAL TEAMS" not in left
    assert "combat-result-art-panel" in right
    assert "combat-result-victory.png" in right
    assert "combat-result-defeat.png" in right
    assert "DEBUG_EFFECT_PLACEHOLDER" not in left
    assert "DEBUG_EFFECT_PLACEHOLDER" not in right
    assert "DEBUG_BLEED" not in left
    assert "DEBUG_BURN" not in right
    assert "actor.effects" in left
    assert "actor.effects" in right
    assert "combat-vital-bar--stamina" in left
    assert "combat-vital-bar--stamina" in right
    assert "ds-panel" not in left
    assert "ds-panel" not in right


def test_combat_css_contains_texture_surfaces_without_shell_overrides():
    source = Path("src/frontend/static/css/pages/game/combat.css").read_text()

    assert ".game-top-row.combat-layout" not in source
    assert ".col-left" not in source
    assert ".col-right" not in source
    assert ".combat-team-bars" in source
    assert ".combat-command-deck" in source
    assert ".combat-feint-row" in source
    assert ".combat-feint-pin" in source
    assert ".combat-feint-cost" in source
    assert ".combat-result-hero" in source
    assert ".combat-result-field" in source
    assert ".combat-result-title--defeat" in source
    assert ".combat-result-empty--progress" in source
    assert ".combat-wait-scene" in source
    assert ".combat-panel" in source
    assert ".combat-vital-bar--stamina i" in source
    assert "button-surface-04-charcoal-stone.webp" in source
    assert "button-surface-02-blackened-metal.webp" in source
    assert "duel-hall.webp" in source
    assert ".combat-log-icon" in source


def test_combat_log_panel_renders_line_icons():
    template = Path("src/frontend/templates/game/domains/combat/viewport/log_panel.html").read_text()

    assert "combat-log-icon" in template
    assert "line.icon_url" in template


def test_combat_result_template_renders_without_result_screen_vm():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/combat/viewport/main.html")

    html = template.render(
        char_id=5,
        combat_result=CombatResultDTO(
            char_id=5,
            combat_id="combat-1",
            title="Поражение",
            message="Бой завершен.",
            summary="Ваша команда проиграла.",
            outcome="defeat",
            archived=False,
            reason="combat_session_finished",
        ),
    )

    assert "Поражение" in html
    assert "ПОЛУЧЕНО ОПЫТА ВСЕГО" in html
    assert "НАВЫКИ НЕ ИЗМЕНИЛИСЬ" in html
    assert "LAST TURN" not in html
    assert "OUTCOME" not in html
    assert 'hx-post="/game/combat/result/continue"' in html
    assert 'hx-vals=\'{"char_id": 5}\'' in html
    assert 'data-target-state="exploration"' in html


def test_combat_result_sidebars_render_without_runtime_screen():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    left = env.get_template("game/domains/combat/left_sidebar/main.html")
    right = env.get_template("game/domains/combat/right_sidebar/main.html")
    result = CombatResultDTO(
        char_id=5,
        combat_id="combat-1",
        title="Поражение",
        message="Бой завершен.",
        summary="Ваша команда проиграла.",
        outcome="defeat",
        archived=True,
        reason="combat_session_finished",
    )

    left_html = left.render(char_id=5, combat_result=result)
    right_html = right.render(char_id=5, combat_result=result)

    assert "status-panel-root" in left_html
    assert "FINAL_ROSTER_NO_DATA" not in left_html
    assert "COMBAT CONTEXT" not in right_html
    assert "AFTERMATH" not in right_html
    assert "combat_session_finished" not in right_html
    assert "combat-result-defeat.png" in right_html
    assert "Поражение" not in right_html


def test_combat_vm_includes_hero_in_allied_side_and_session_metrics():
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=3,
        status="active",
        hero=CombatActorCardDTO(
            actor_id="1",
            name="Hero",
            team="team_1",
            vitals=CombatActorVitalsDTO(hp_current=70, hp_max=100),
        ),
        target=CombatActorCardDTO(
            actor_id="2",
            name="Shadow",
            team="team_2",
            vitals=CombatActorVitalsDTO(hp_current=40, hp_max=80),
        ),
        enemies=[
            CombatActorCardDTO(
                actor_id="2",
                name="Shadow",
                team="team_2",
                vitals=CombatActorVitalsDTO(hp_current=40, hp_max=80),
                is_target=True,
            )
        ],
    )

    screen = build_combat_screen_vm(dashboard)

    assert [actor.actor_id for actor in screen.allies] == ["1"]
    assert screen.allied_team.hp_current == 70
    assert screen.allied_team.hp_max == 100
    assert screen.enemy_team.hp_current == 40
    assert screen.enemy_team.hp_max == 80
    assert screen.allied_team.target_queue_size == 0
    assert screen.enemy_team.pending_action_count == 0


def test_combat_vm_exposes_full_token_strip_from_backend_key_values():
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=3,
        status="active",
        hero=CombatActorCardDTO(
            actor_id="1",
            name="Hero",
            team="team_1",
            tokens={"hit": 2, "gift": 1},
            vitals=CombatActorVitalsDTO(hp_current=70, hp_max=100),
        ),
    )

    screen = build_combat_screen_vm(dashboard)

    assert [token.token_id for token in screen.token_bar] == [
        "tempo",
        "hit",
        "crit",
        "dodge",
        "parry",
        "block",
        "counter",
        "gift",
    ]
    assert [token.value for token in screen.token_bar] == [0, 2, 0, 0, 0, 0, 0, 1]
    assert screen.token_bar[1].icon_url.endswith("/token-hit.svg")
    assert screen.token_bar[-1].icon_url.endswith("/token-gift.svg")
    assert screen.token_bar[0].catalog == "combat_tokens"
    assert screen.token_bar[0].catalog_key == "tempo"


def test_combat_vm_effect_badge_shows_remaining_turns_not_absolute_expire_exchange():
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=7,
        status="active",
        hero=CombatActorCardDTO(
            actor_id="1",
            name="Hero",
            team="team_1",
            exchange_counter=6,
            vitals=CombatActorVitalsDTO(hp_current=30, hp_max=40),
            active_effects=[
                CombatEffectBadgeDTO(effect_id="dot_bleed", expires_at_exchange=8, impact={"hp": -1}),
            ],
        ),
    )

    screen = build_combat_screen_vm(dashboard)

    effect = screen.hero.effects[0]
    assert effect.duration_text == "3"
    assert effect.title == "Кровотечение"
    assert effect.tooltip == "Кровотечение // осталось 3 хода // -1 HP за ход"


def test_combat_vm_marks_pinned_feints_and_costs():
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=3,
        status="active",
        hero=CombatActorCardDTO(
            actor_id="1",
            name="Hero",
            team="team_1",
            feints=[CombatFeintOptionDTO(feint_id="true_strike", cost={"hit": 2}, pinned=True)],
        ),
    )

    screen = build_combat_screen_vm(dashboard)

    assert screen.feint_options[0].pinned is True
    assert screen.feint_options[0].cost == {"hit": 2}
    assert screen.feint_options[0].cost_items[0].token_id == "hit"
    assert screen.feint_options[0].cost_items[0].amount == 2
    assert screen.feint_options[0].cost_items[0].icon_url.endswith("/token-hit.svg")
    assert screen.feint_options[0].cost_items[0].catalog_key == "hit"


def test_combat_vm_preserves_log_catalog_metadata():
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=3,
        status="active",
        hero=CombatActorCardDTO(actor_id="1", name="Hero", team="team_1"),
        events_delta=CombatDeltaDTO(
            events=[
                CombatEventDTO(
                    type="HIT",
                    text="Верный удар попадает по цели.",
                    global_turn=7,
                    data={
                        "catalog": "combat_entries",
                        "catalog_key": "combat.feint.true_strike",
                        "catalog_event": "hit",
                        "catalog_taxonomy": "humanoid",
                        "catalog_tooltip": "description",
                    },
                )
            ],
            turns=[
                CombatLogTurnDTO(
                    global_turn=7,
                    title="Ход 7",
                    entries=[
                        CombatEventDTO(
                            type="HIT",
                            text="Верный удар попадает по цели.",
                            data={
                                "global_turn": 7,
                                "catalog": "combat_entries",
                                "catalog_key": "combat.feint.true_strike",
                            },
                        )
                    ],
                )
            ],
        ),
    )

    screen = build_combat_screen_vm(dashboard)

    assert screen.log_lines[0].catalog == "combat_entries"
    assert screen.log_lines[0].global_turn == 7
    assert screen.log_lines[0].catalog_key == "combat.feint.true_strike"
    assert screen.log_lines[0].catalog_event == "hit"
    assert screen.log_lines[0].catalog_tooltip == "description"
    assert screen.log_lines[0].icon_url is not None
    assert screen.log_lines[0].icon_url.endswith("/feint.svg")
    assert screen.log_turns[0].global_turn == 7
    assert screen.log_turns[0].title == "Ход 7"
    assert screen.log_turns[0].lines[0].catalog_key == "combat.feint.true_strike"
    assert screen.log_turns[0].lines[0].icon_url is not None
    assert screen.log_turns[0].lines[0].icon_url.endswith("/feint.svg")


def test_combat_result_vm_builds_report_and_progression_rows():
    result = CombatResultDTO(
        combat_id="combat-1",
        char_id=7,
        status="finished",
        outcome="victory",
        title="Победа",
        summary="Ваша команда победила.",
        reason="combat_session_finished",
        archived=True,
        teams={"team_1": ["7"], "team_2": ["-7"]},
        actors={
            "7": {
                "name": "CodexDLC",
                "team": "team_1",
                "vitals_final": {"hp": 25, "max_hp": 40},
                "progression": {"skill_swords": 0.0003},
            },
            "-7": {
                "name": "Shadow CodexDLC",
                "team": "team_2",
                "is_dead": True,
                "vitals_final": {"hp": 0, "max_hp": 40},
            },
        },
        report={
            "last_turn": 9,
            "turns": 4,
            "teams": [
                {"team": "team_1", "outcome": "victory", "actors": [{"actor_id": "7"}]},
                {"team": "team_2", "outcome": "defeat", "actors": [{"actor_id": "-7"}]},
            ],
        },
        rewards={"progression": {"skill_swords": 0.0003}},
        metadata={"battle_type": "arena"},
        primary_action=CombatResultActionDTO(label="Продолжить", target_state="arena"),
    )

    screen = build_combat_result_screen_vm(result)

    assert screen.combat_id == "combat-1"
    assert screen.last_turn == 9
    assert screen.battle_type == "arena"
    assert [team.label for team in screen.teams] == ["Победили", "Проиграли"]
    assert screen.teams[0].actors[0].name == "CodexDLC"
    assert screen.teams[0].actors[0].hp_percent == 62
    assert screen.progression[0].label == "Мечи"
    assert screen.progression[0].amount_text == "+0.0003"
    assert screen.progression[0].percent_text == "+0.03%"
    assert screen.experience.amount_text == "+0.0003"
    assert screen.experience.percent_text == "+0.03%"
    assert screen.primary_target_state == "arena"


def test_combat_result_vm_builds_standard_combat_sidebars_from_finalization():
    result = CombatResultDTO(
        combat_id="combat-1",
        char_id=7,
        status="finished",
        outcome="victory",
        teams={"team_1": ["7"], "team_2": ["-7"]},
        actors={
            "7": {
                "name": "CodexDLC",
                "team": "team_1",
                "vitals_final": {"hp": 25, "max_hp": 40, "en": 12, "max_en": 20, "stamina": 80, "max_stamina": 100},
            },
            "-7": {
                "name": "Shadow CodexDLC",
                "team": "team_2",
                "actor_type": "shadow",
                "is_dead": True,
                "vitals_final": {"hp": 0, "max_hp": 40},
            },
        },
        report={"last_turn": 9},
        metadata={"viewer_team": "team_1", "winner": "team_1", "battle_type": "arena"},
    )

    screen = build_combat_screen_from_result_vm(result)

    assert screen.status == "finished"
    assert screen.action_state == "COMBAT_FINALIZED"
    assert screen.hero.name == "CodexDLC"
    assert screen.hero.vitals.hp_current == 25
    assert screen.target is not None
    assert screen.target.name == "Shadow CodexDLC"
    assert screen.target.is_dead is True
    assert screen.allied_team.total_count == 1
    assert screen.enemy_team.alive_count == 0

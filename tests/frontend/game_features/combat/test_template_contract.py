from pathlib import Path

from src.frontend.game_features.combat.view_models.screen import build_combat_screen_vm
from src.shared.schemas.combat import CombatActorCardDTO, CombatActorVitalsDTO, CombatDashboardDTO


def test_combat_shell_forces_three_zone_layout():
    template = Path("src/frontend/templates/game/session_content_inner.html").read_text()

    assert "combat_layout = domain == 'combats'" in template
    assert "'combat-layout' if combat_layout else ''" in template
    assert "combat_layout or (session_ui and session_ui.left_open)" in template
    assert "combat_layout or (session_ui and session_ui.right_open)" in template


def test_combat_viewport_uses_stage_and_command_deck():
    template = Path("src/frontend/templates/game/domains/combat/viewport/main.html").read_text()

    assert "combat-viewport" in template
    assert "combat-screen-shell" in template
    assert "combat-battle-header" in template
    assert "combat-team-overview" in template
    assert "combat_screen.session_id" not in template
    assert "QUEUE" in template
    assert "LOCKED" in template
    assert "combat-stage" in template
    assert "combat-duelist--hero" in template
    assert "combat-duelist--target" in template
    assert "combat-command-deck" in template
    assert "combat-log-panel" in template
    assert "combat_result" in template
    assert "combat-result-modal" in template
    assert "combat_result.primary_action.target_state" in template
    assert "ds-panel combat-summary" not in template


def test_combat_sidebars_use_combat_panels():
    left = Path("src/frontend/templates/game/domains/combat/left_sidebar/main.html").read_text()
    right = Path("src/frontend/templates/game/domains/combat/right_sidebar/main.html").read_text()

    assert "combat-panel combat-actor-panel" in left
    assert "combat-panel combat-actor-panel" in right
    assert "combat-panel-header" in left
    assert "combat-panel-header" in right
    assert "ds-panel" not in left
    assert "ds-panel" not in right


def test_combat_css_contains_texture_surfaces_without_shell_overrides():
    source = Path("src/frontend/static/css/pages/game/combat.css").read_text()

    assert ".game-top-row.combat-layout" not in source
    assert ".col-left" not in source
    assert ".col-right" not in source
    assert ".combat-stage" in source
    assert ".combat-command-deck" in source
    assert ".combat-result-modal" in source
    assert ".combat-panel" in source
    assert "button-surface-04-charcoal-stone.webp" in source
    assert "button-surface-02-blackened-metal.webp" in source
    assert "duel-hall.webp" in source


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

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.frontend.game_features.combat.view_models.screen import (
    build_combat_outcome_screen_from_dashboard_vm,
    build_combat_outcome_screen_from_result_vm,
    build_combat_result_screen_vm,
    build_combat_screen_from_result_vm,
    build_combat_screen_vm,
)
from src.shared.schemas.combat import (
    CombatActionOptionDTO,
    CombatActorCardDTO,
    CombatActorStatSheetDTO,
    CombatActorVitalsDTO,
    CombatDashboardDTO,
    CombatDeltaDTO,
    CombatEffectBadgeDTO,
    CombatEventDTO,
    CombatExchangeStateDTO,
    CombatFeintOptionDTO,
    CombatLogActorRefDTO,
    CombatLogTurnDTO,
    CombatResultActionDTO,
    CombatResultDTO,
    CombatStatSectionDTO,
    CombatStatValueDTO,
)


def test_combat_shell_uses_desktop_docks_without_forcing_mobile_panels():
    template = Path("src/frontend/templates/game/session_content_inner.html").read_text()
    responsive_dir = Path("src/frontend/static/css/game/shell/responsive")
    combat_desktop_css = responsive_dir.joinpath("combat_desktop.css").read_text()
    tablet_css = responsive_dir.joinpath("tablet_drawers.css").read_text()
    mobile_css = responsive_dir.joinpath("mobile_drawers.css").read_text()

    assert "combat_layout = domain == 'combats'" in template
    assert "shell_background_url = background_url" in template
    assert "scene-none" not in template
    assert "localStorage.getItem('combat_background_url')" in template
    assert "'combat-layout' if combat_layout else ''" in template
    assert "shell_left_open" not in template
    assert "shell_right_open" not in template
    assert "session_ui" not in template
    assert "x-init=\"rightPanelView = 'enemies'\"" in template
    assert (
        "{% if domain == 'combats' %}\n"
        "                        {% include \"game/domains/combat/left_sidebar/main.html\" %}\n"
        "                    {% else %}\n"
        "                    <div x-show=\"leftPanelView === 'status'\">"
    ) in template
    assert '{% if domain in [\'combats\', \'death\', \'loot\'] %}x-show="true"' in template
    assert "@media (min-width: 1025px)" in combat_desktop_css
    assert ".game-top-row.combat-layout" in combat_desktop_css
    assert "grid-template-columns: var(--side-panel-width) minmax(0, 1fr) var(--side-panel-width);" in combat_desktop_css
    assert ".game-top-row.combat-layout .col-left" in combat_desktop_css
    assert ".game-top-row.combat-layout .col-right" in combat_desktop_css
    assert ".game-top-row.combat-layout .combat-screen-shell" in combat_desktop_css
    assert "--center-content-max: 100%;" in combat_desktop_css
    assert "@media (max-width: 1279px)" in tablet_css
    assert "@media (max-width: 767px)" in mobile_css
    assert ".game-top-row.combat-layout .col-left,\n    .game-top-row.combat-layout .col-right {\n        display: none !important;" not in combat_desktop_css


def test_combat_shell_renders_standard_header_without_footer_chat():
    base = Path("src/frontend/templates/game/base_game.html").read_text()
    session_oob = Path("src/frontend/templates/game/session_content.html").read_text()
    header = Path("src/frontend/templates/game/includes/header.html").read_text()

    assert 'domain != \'combats\'' not in base
    assert 'domain != \'combats\'' not in session_oob
    assert 'include "game/includes/chat_footer.html"' not in base
    assert 'include "game/includes/chat_footer.html"' not in session_oob
    assert 'include "game/includes/chat_overlay.html"' in base
    assert 'include "game/includes/chat_overlay.html"' in session_oob
    assert "{% if domain == 'combats' %}" not in header
    assert "combat-header-state" not in header
    assert "combat-header-actions" not in header
    assert "combat-header-panel-toggle" not in header
    assert "game-system-menu" in header
    assert 'include "game/domains/game_menu/header_nav.html"' not in header


def test_combat_stat_groups_persist_open_state_across_swaps():
    left = Path("src/frontend/templates/game/domains/combat/left_sidebar/main.html").read_text()
    right = Path("src/frontend/templates/game/domains/combat/right_sidebar/main.html").read_text()
    js_source = Path("src/frontend/static/js/core/main.js").read_text()
    js_bundle = Path("src/frontend/static/js/game.js").read_text()

    assert 'data-combat-stat-key="hero:{{ actor.actor_id }}:{{ section.key }}"' in left
    assert 'data-combat-stat-key="ally:{{ ally.actor_id }}:{{ section.key }}"' in left
    assert 'data-combat-stat-key="enemy:{{ enemy.actor_id }}:{{ section.key }}"' in right
    assert "tbmmorpg:combat:stat-section:" in js_source
    assert "initCombatStatSectionPersistence(document);" in js_source
    assert "initCombatStatSectionPersistence(document);" in js_bundle


def test_combat_viewport_uses_prototype_field_and_bottom_action_panel():
    template = Path("src/frontend/templates/game/domains/combat/viewport/main.html").read_text()
    exchange_card = Path("src/frontend/templates/game/domains/combat/viewport/exchange_card.html").read_text()

    assert "combat-screen-shell" in template
    assert "combat-center-menu" in template
    assert "leftOpen = false; rightOpen = false" in template
    assert "nav.l1 if nav else none, 'PARTY'" in template
    assert "nav.r1 if nav else none, 'FOES'" in template
    assert "nav.r2 if nav else none, 'LOG'" in template
    assert "item.label or fallback_label" in template
    assert "combat-statebar" in template
    assert "combat-viewport" not in template
    assert 'id="center-screens"' not in template
    assert "cs active" not in template
    assert "game-screen-area" not in template
    assert "game-screen-area--vertical" not in template
    assert "combat-battle-header" not in template
    assert "combat-team-bars" not in template
    assert "combat-command-deck" not in template
    assert "combat-exchange-track" not in template
    assert "combat-exchange-meta" not in template
    assert "combat-secondary-action" not in template
    assert "combat-escape" not in template
    assert "СБЕЖАТЬ" not in template
    assert "game-action-panel game-action-panel--bottom combat-action-panel" in template
    assert "game-action-button" in template
    assert "combat-action-panel" in template
    assert "combat-mobile-dock" not in template
    assert "QUEUE" in template
    assert "combat-stage" not in template
    assert "combat-duelist--hero" not in template
    assert "combat-duelist--target" not in template
    assert "combat-field" in template
    assert "combat-commit--{{ field_target.commit_state }}" in template
    assert "combat-commit-frame--{{ field_target.commit_state }}" in template
    assert "field_target.commit_tooltip" in template
    assert 'aria-label="Enemy effects"' in template
    assert 'aria-label="Player effects"' in template
    assert "combat-effect-stack combat-effect-stack--field" in template
    assert "combat-effect combat-effect--{{ effect.frame_kind }}" in template
    assert "data-tippy-content=\"{{ effect.tooltip }}\"" in template
    assert "{{ effect.title }}{% if effect.duration_text %} {{ effect.duration_text }}{% endif %}" not in template
    assert "combat-effect-empty" in template
    assert "combat-exchange-card" in exchange_card
    assert "combat-exchange-trigger" in exchange_card
    assert "ТЕКУЩИЙ РАЗМЕН" in exchange_card
    assert "combat-exchange-inline" in exchange_card
    assert "combat-exchange-modal" in exchange_card
    assert "ПОСЛЕДНИЙ РАЗМЕН" in exchange_card
    assert "combat-exchange-wave" in exchange_card
    assert 'import "game/domains/combat/viewport/log_line_macros.html" as combat_log' in exchange_card
    assert "combat_log.combat_log_display_text(line.text)" in exchange_card
    assert "combat_log.combat_log_facts(line, data)" in exchange_card
    assert "data-source-id" in exchange_card
    assert "data-target-id" in exchange_card
    assert "combat-battle-log" in exchange_card
    assert 'combat_log_panel_id = "combat-battle-log-panel"' in exchange_card
    assert "combat_screen.log_pages" in exchange_card
    assert 'include "game/domains/combat/viewport/log_panel.html"' in exchange_card
    assert 'include "game/domains/combat/viewport/exchange_card.html"' in template
    assert "combat_screen.log_turns[0]" not in template
    assert "combat_screen.exchange_state" in template
    assert "combat_screen.target_exchange_turn" in exchange_card
    assert "target_exchange.lines" in exchange_card
    assert "target_exchange.lines[:4]" not in exchange_card
    assert 'hx-trigger="every 2s"' not in template
    assert 'hx-trigger="load delay:1500ms"' in template
    assert "combat_screen.action_state == 'WAITING_FOR_RESPONSES'" in template
    assert 'hx-disabled-elt="this"' in template
    assert "WAITING_FOR_RESPONSES" in template
    assert "REFRESH_TARGET" in template
    assert "combat-primary-row" in template
    assert "combat-command-layout" in template
    assert "combat-token-strip" in template
    assert 'data-catalog="{{ token.catalog }}"' in template
    assert 'data-catalog-tooltip="description"' in template
    assert "feint_slots = combat_screen.feint_options[:3]" in template
    assert "[:3 - (feint_slots|length)]" in template
    assert "combat-feint-row" in template
    assert 'hx-post="/game/combat/feint-pin"' in template
    assert "action.pinned" in template
    assert 'data-catalog="{{ action.catalog }}"' in template
    assert 'data-catalog-field="title"' in template
    assert 'data-catalog-field="label"' not in template
    assert "action.cost_tooltip" in template
    assert 'data-catalog-tooltip-extra="{{ action.cost_tooltip }}"' not in template
    assert "combat-feint-cost" not in template
    assert "combat_screen.ability_options" in template
    assert "ability_source is mapping" in template
    assert "ability_source is sequence" in template
    assert "combat-ability-strip" in template
    assert "combat-ability-tooltip-host" in template
    assert 'data-catalog-tooltip="ability"' in template
    assert "ability_slots = ability_options" in template
    assert "belt_slots = hero.quick_belt[:8]" not in template
    assert "ability_slots = ability_options[:8]" not in template
    assert "[:8 - (belt_slots|length)]" not in template
    assert "[:8 - (ability_slots|length)]" in template
    assert "combat-belt-slot--empty" not in template
    assert "combat-ability-option--empty" in template
    assert "/static/images/ui/inventory-gear/default.svg" in template
    assert "<span>x</span>" not in template
    assert "combat-action-group--desktop" not in template
    assert "combat-action-group--mobile" not in template
    assert "panel-dock panel-dock--framed combat-action-group combat-action-group--belt" not in template
    assert "panel-dock panel-dock--framed combat-action-group combat-action-group--abilities" not in template
    assert "combat-ability-option" in template
    assert template.index("combat-token-strip") < template.index("combat-ability-strip")
    assert "ability-debug-swirl.svg" not in template
    assert "DEBUG_ABILITY_PLACEHOLDER" not in template
    assert 'include "game/domains/combat/viewport/log_panel.html"' not in template
    assert "combat_result" in template
    assert "combat_outcome_screen" in template
    assert "combat-result-hero" in template
    assert "combat-result-visual" in template
    assert "combat-result-summary" in template
    assert "combat-result-log" in template
    assert "combat-result-field" in template
    assert "combat-result-report" in template
    assert "combat-result-rewards" in template
    assert "combat-outcome-tabs" in template
    assert "SUMMARY" in template
    assert "LOG" in template
    assert "outcomeTab === 'summary'" in template
    assert "outcomeTab === 'log'" in template
    assert "/game/combat/logs?char_id={{ char_id }}" in template
    assert "loadOutcomeLog()" in template
    assert "htmx.ajax('GET', '/game/combat/logs?char_id={{ char_id }}" in template
    assert 'x-ref="outcomeLogHost"' in template
    assert 'data-loaded="0"' in template
    assert "combat-outcome-log-panel" in template
    assert "ПОЛУЧЕНО ОПЫТА ВСЕГО" in template
    assert "НАВЫКИ НЕ ИЗМЕНИЛИСЬ" in template
    assert "result_primary_state" in template
    assert "'Противники · ' ~ team.team|upper" in template
    assert template.index("combat-result-visual") < template.index("combat-result-summary")
    assert template.index("combat-result-summary") < template.index("combat-result-actions")
    assert template.index("combat-result-field") < template.index("combat-result-head")
    assert "OUTCOME" not in template
    assert "ARCHIVE" not in template
    assert "combat-wait-scene" not in template
    assert "ds-panel combat-summary" not in template


def test_combat_exchange_card_uses_only_latest_current_target_exchange():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/combat/viewport/main.html")
    hero_ref = CombatLogActorRefDTO(id="1", name="Hero", team="team_1")
    current_target_ref = CombatLogActorRefDTO(id="2", name="Goblin Cutter", team="team_2")
    other_target_ref = CombatLogActorRefDTO(id="3", name="Goblin Scavenger", team="team_2")
    hero = CombatActorCardDTO(actor_id="1", name="Hero", team="team_1")
    target = CombatActorCardDTO(actor_id="2", name="Goblin Cutter", team="team_2", is_target=True)

    screen = build_combat_screen_vm(
        CombatDashboardDTO(
            session_id="combat-1",
            turn_number=9,
            status="active",
            action_state="ACTION_READY",
            hero=hero,
            target=target,
            enemies=[target],
            events_delta=CombatDeltaDTO(
                turns=[
                    CombatLogTurnDTO(
                        global_turn=9,
                        title="Ход 9",
                        entries=[
                            CombatEventDTO(
                                type="HIT",
                                text="Hero hits current target.",
                                source=hero_ref,
                                target=current_target_ref,
                                global_turn=9,
                                resources=[
                                    {"actor_id": "2", "resource": "hp", "before": 40, "after": 31, "max": 40, "delta": -9}
                                ],
                            ),
                            CombatEventDTO(
                                type="HIT",
                                text="Other enemy is hit by area attack.",
                                source=hero_ref,
                                target=other_target_ref,
                                global_turn=9,
                            ),
                            CombatEventDTO(
                                type="HIT",
                                text="Current target counters Hero.",
                                source=current_target_ref,
                                target=hero_ref,
                                global_turn=9,
                            ),
                        ],
                    ),
                    CombatLogTurnDTO(
                        global_turn=8,
                        title="Ход 8",
                        entries=[
                            CombatEventDTO(
                                type="HIT",
                                text="Older current target exchange.",
                                source=hero_ref,
                                target=current_target_ref,
                                global_turn=8,
                            )
                        ],
                    ),
                ]
            ),
        )
    )

    html = template.render(char_id=1, combat_screen=screen, combat_result=None)

    assert screen.target_exchange_turn is not None
    assert screen.target_exchange_turn.global_turn == 9
    assert [line.text for line in screen.target_exchange_turn.lines] == [
        "Hero hits current target.",
        "Current target counters Hero.",
    ]
    assert "Hero hits current target." in html
    assert "Current target counters Hero." in html
    target_exchange_html = html.split("combat-battle-log", maxsplit=1)[0]
    battle_log_html = html.split("combat-battle-log", maxsplit=1)[1]
    assert "combat-log-facts" in target_exchange_html
    assert "[HP 31/40]" in target_exchange_html
    assert "token-counter.svg" not in target_exchange_html
    assert 'data-source-id="1"' in target_exchange_html
    assert 'data-target-id="2"' in target_exchange_html
    assert "Other enemy is hit by area attack." not in target_exchange_html
    assert "Older current target exchange." not in target_exchange_html
    assert "Other enemy is hit by area attack." in battle_log_html
    assert "Older current target exchange." in battle_log_html
    assert 'id="combat-battle-log-panel"' in battle_log_html
    assert "hx-target=\"#combat-battle-log-panel\"" in battle_log_html
    assert "embedded=1" in battle_log_html
    assert "2</b>" in html
    assert "3</b>" not in html


def test_combat_empty_target_state_does_not_duplicate_exchange_text():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/combat/viewport/main.html")
    hero = CombatActorCardDTO(actor_id="1", name="Hero", team="team_1")
    screen = build_combat_screen_vm(
        CombatDashboardDTO(
            session_id="combat-empty-target",
            turn_number=17,
            status="active",
            action_state="TARGET_QUEUE_EMPTY",
            hero=hero,
            target=None,
            exchange_state=CombatExchangeStateDTO(
                pair_status="no_target",
                opponent_response_state="unknown",
                title="NO ACTIVE EXCHANGE",
                summary_text="Очередь целей пуста. Активного размена нет.",
            ),
        )
    )

    html = template.render(char_id=1, combat_screen=screen, combat_result=None)

    assert "combat-target-empty-card" not in html
    assert html.count("NO ACTIVE EXCHANGE") == 1
    assert html.count("Очередь целей пуста. Активного размена нет.") == 1


def test_combat_template_renders_draggable_actor_stat_sheet():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/session_content_inner.html")
    stat_sheet = CombatActorStatSheetDTO(
        actor_id="2",
        name="Shadow",
        total_count=2,
        sections=[
            CombatStatSectionDTO(
                key="defense",
                label="DEFENSE",
                items=[
                    CombatStatValueDTO(
                        key="parry",
                        label="PARRY",
                        value=12,
                        value_text="12",
                        tooltip="Оружие: 7 // Статы: 5 из 14",
                    ),
                    CombatStatValueDTO(key="block", label="BLOCK", value=7.5, value_text="7.5"),
                ],
            )
        ],
    )
    hero = CombatActorCardDTO(actor_id="1", name="Hero", team="team_1")
    target = CombatActorCardDTO(actor_id="2", name="Shadow", team="team_2", is_target=True, stat_sheet=stat_sheet)
    screen = build_combat_screen_vm(
        CombatDashboardDTO(
            session_id="combat-stats",
            turn_number=1,
            status="active",
            action_state="ACTION_READY",
            hero=hero,
            target=target,
            enemies=[target],
        )
    )

    html = template.render(char_id=1, domain="combats", combat_screen=screen, combat_result=None)

    assert "combat-stat-trigger" in html
    assert "activeStatSheet: null" in html
    assert "@keydown.escape.window=\"activeStatSheet = null\"" in html
    assert "openStatSheet('enemy-2')" in html
    assert "openStatSheet('hero')" not in html
    assert "Защита" in html
    assert "PARRY" in html
    assert "7.5" in html
    assert 'data-tippy-content="Оружие: 7 // Статы: 5 из 14"' in html


def test_combat_vm_localizes_archived_actor_stat_labels():
    stat_sheet = CombatActorStatSheetDTO(
        actor_id="2",
        name="goblin_slinger",
        total_count=5,
        sections=[
            CombatStatSectionDTO(
                key="offense",
                label="OFFENSE",
                items=[
                    CombatStatValueDTO(key="main_hand_damage", label="MH DAMAGE", value=8, value_text="7 — 9"),
                    CombatStatValueDTO(key="main_hand_accuracy", label="MH ACCURACY", value=61, value_text="61%"),
                    CombatStatValueDTO(
                        key="anti_dodge_chance",
                        label="ANTI-DODGE",
                        value=0.565,
                        value_text="56.5%",
                    ),
                    CombatStatValueDTO(
                        key="armor_penetration_pct",
                        label="ARMOR PEN",
                        value=0.024,
                        value_text="2.4%",
                    ),
                    CombatStatValueDTO(
                        key="physical_suppression",
                        label="PHYS SUPPRESS",
                        value=0.262,
                        value_text="26.2%",
                    ),
                ],
            )
        ],
    )
    target = CombatActorCardDTO(
        actor_id="2",
        name="goblin_slinger",
        team="team_2",
        is_target=True,
        stat_sheet=stat_sheet,
    )

    screen = build_combat_screen_vm(
        CombatDashboardDTO(
            session_id="combat-stats",
            turn_number=1,
            status="active",
            hero=CombatActorCardDTO(actor_id="1", name="Hero", team="team_1"),
            target=target,
            enemies=[target],
        )
    )

    assert screen.target is not None
    assert screen.target.name == "гоблин-лучник"
    assert screen.target.stat_sheet is not None
    section = screen.target.stat_sheet.sections[0]
    assert section.label == "Атака"
    assert [item.label for item in section.items] == [
        "Урон",
        "Точность",
        "Против уворота",
        "Пробой брони",
        "Подавление защиты",
    ]


def test_combat_active_template_renders_prototype_layout():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/combat/viewport/main.html")
    hero = CombatActorCardDTO(
        actor_id="1",
        name="Hero",
        team="team_1",
        vitals=CombatActorVitalsDTO(hp_current=70, hp_max=100),
        feints=[CombatFeintOptionDTO(feint_id="true_strike", label="Attack", cost={"hit": 1})],
    )
    target = CombatActorCardDTO(
        actor_id="2",
        name="Shadow",
        team="team_2",
        vitals=CombatActorVitalsDTO(hp_current=40, hp_max=80),
        is_target=True,
    )
    hero_ref = CombatLogActorRefDTO(id="1", name="Hero", team="team_1")
    target_ref = CombatLogActorRefDTO(id="2", name="Shadow", team="team_2")
    screen = build_combat_screen_vm(
        CombatDashboardDTO(
            session_id="combat-1",
            turn_number=3,
            status="active",
            action_state="ACTION_READY",
            hero=hero,
            target=target,
            allies=[hero],
            enemies=[target],
            events_delta=CombatDeltaDTO(
                turns=[
                    CombatLogTurnDTO(
                        global_turn=3,
                        title="Ход 3",
                        entries=[
                            CombatEventDTO(
                                type="HIT",
                                text="Shadow hits Hero.",
                                source=target_ref,
                                target=hero_ref,
                                global_turn=3,
                            )
                        ],
                    )
                ]
            ),
        )
    )

    html = template.render(char_id=5, combat_screen=screen, combat_result=None)

    assert "combat-statebar" in html
    assert "combat-viewport" not in html
    assert 'id="center-screens"' not in html
    assert "cs active" not in html
    assert "game-screen-area" not in html
    assert "game-action-panel game-action-panel--bottom combat-action-panel" in html
    assert "combat-field" in html
    assert "combat-exchange-wave" in html
    assert "Shadow hits Hero." in html
    assert "combat-mobile-dock" not in html
    assert "combat-action-panel" in html
    assert "combat-team-bars" not in html
    assert "СБЕЖАТЬ" not in html


def test_combat_sidebars_use_combat_panels():
    left = Path("src/frontend/templates/game/domains/combat/left_sidebar/main.html").read_text()
    right = Path("src/frontend/templates/game/domains/combat/right_sidebar/main.html").read_text()
    active_left = left.split("{% elif combat_screen %}", maxsplit=1)[1].split("{% else %}", maxsplit=1)[0]

    assert "combat-panel combat-actor-panel" in left
    assert "combat-panel combat-actor-panel" not in active_left
    assert "status-widget-card scenario-status-card combat-side-summary-card combat-side-summary-card--left" in active_left
    assert "combat-side-summary-effects" in active_left
    assert "combat-panel combat-actor-panel" not in right.split("{% elif combat_screen %}", maxsplit=1)[1].split("{% else %}", maxsplit=1)[0]
    assert "combat-panel-header" in left
    assert "combat-panel-header" in right
    assert "Status panel actions" in left
    assert "Party panel actions" in left
    assert "$dispatch('panel-toggle', { side: 'left', view: 'status' })" in left
    assert "$dispatch('panel-toggle', { side: 'left', view: 'allies' })" in left
    assert "activeStatSheet && activeStatSheet.startsWith('ally-')" in left
    assert "combat-actor-name--with-action" not in left
    assert "openStatSheet('hero')" not in left
    assert "openStatSheet('ally-{{ ally.actor_id }}')" in left
    assert "{{ ally.queue_state }}" not in left
    assert "rightPanelView === 'enemies'" in right
    assert "rightPanelView === 'log'" in right
    assert "combat-drawer-log-panel" in right
    assert "combat-context-panel" not in right
    assert "combat_screen.exchange_state.pair_status" not in right
    assert "combat_screen.exchange_state.opponent_response_state" not in right
    assert "<button class=\"dock-nav-button is-active\" type=\"button\">FOES</button>" in right
    assert "default_enemy_id = combat_screen.target.actor_id" in right
    assert "status-widget-card scenario-status-card combat-side-summary-card combat-side-summary-card--right combat-enemy-summary-card" in right
    assert "status-widget-avatar combat-side-summary-avatar combat-enemy-summary-avatar" in right
    assert "status-widget-bar status-widget-bar--hp" in right
    assert "enemy.vitals.hp_current" in right
    assert "combat-enemy-summary-effects" in right
    assert "combat-panel combat-roster-panel\"" in right
    assert "combat-panel combat-roster-panel\"\n                     x-show" not in right
    assert "combat-commit-row--{{ enemy.commit_state }}" in right
    assert "combat-queue-dot--{{ enemy.commit_state }}" in right
    assert "enemy.commit_tooltip" in right
    assert "combat_screen.enemy_groups" in right
    assert "combat-roster-group" in right
    assert "combat-roster-info-button" in right
    assert "openStatSheet('enemy-{{ enemy.actor_id }}')" in right
    assert "{{ enemy.queue_state }}" not in right
    assert 'data-team="{{ enemy.team }}"' in right
    assert "combat-target-empty-panel" in right
    assert "TARGET_QUEUE_EMPTY" in right
    assert "Цель не найдена" in right
    assert "combat_result" in left
    assert "FINAL PLAYER STATE" in left
    assert "FINAL TEAMS" not in left
    assert "combat-result-art-panel" in right
    assert "combat-result-victory.webp" in right
    assert "combat-result-defeat.webp" in right
    assert "DEBUG_EFFECT_PLACEHOLDER" not in left
    assert "DEBUG_EFFECT_PLACEHOLDER" not in right
    assert "DEBUG_BLEED" not in left
    assert "DEBUG_BURN" not in right
    assert "actor.effects" in left
    assert "actor.effects" not in right.split("{% elif combat_screen %}", maxsplit=1)[1].split("{% else %}", maxsplit=1)[0]
    assert "combat-vital-bar--stamina" in left
    assert "ds-panel" not in left
    assert "ds-panel" not in right


def test_combat_css_contains_texture_surfaces_without_shell_overrides():
    combat_dir = Path("src/frontend/static/css/game/domains/combat")
    index = combat_dir.joinpath("index.css").read_text()
    screen = combat_dir.joinpath("screen.css").read_text()
    actions = combat_dir.joinpath("actions.css").read_text()
    logs = combat_dir.joinpath("logs.css").read_text()
    result = combat_dir.joinpath("result.css").read_text()
    responsive = combat_dir.joinpath("responsive.css").read_text()
    source = "\n".join(
        path.read_text()
        for path in (
            combat_dir / "screen.css",
            combat_dir / "teams.css",
            combat_dir / "actions.css",
            combat_dir / "logs.css",
            combat_dir / "sidebars.css",
            combat_dir / "result.css",
            combat_dir / "prototype.css",
        )
    )

    assert ".game-top-row.combat-layout" not in source
    assert ".col-left" not in source
    assert ".col-right" not in source
    assert '@import url("screen.css");' in index
    assert '@import url("prototype.css");' in index
    assert ".combat-team-bars" in combat_dir.joinpath("teams.css").read_text()
    assert ".combat-battle-log--drawer" in actions
    assert ".combat-battle-log--drawer {\n    display: grid;\n}" in actions
    assert ".combat-command-deck" in actions
    assert ".combat-feint-row" in actions
    assert ".combat-feint-pin" in actions
    assert ".combat-feint-cost" not in actions
    assert ".combat-log-list" in logs
    assert ".combat-result-hero" in result
    assert ".combat-result-visual" in result
    assert ".combat-result-summary" in result
    assert ".combat-result-field" in result
    assert ".combat-result-title--defeat" in result
    assert ".combat-result-empty--progress" in result
    assert "grid-template-rows: auto minmax(260px, .72fr) minmax(0, auto) auto;" in result
    assert ".combat-result-head {\n    position: absolute;" in result
    assert ".combat-result-actions" in result
    assert ".combat-result-actions .combat-primary-action" in result
    assert "position: sticky;" in result
    assert ".combat-wait-scene" in source
    assert ".combat-panel" in source
    assert ".combat-vital-bar--stamina i" in source
    assert "button-surface-04-charcoal-stone.webp" in source
    assert "button-surface-02-blackened-metal.webp" in source
    action_panel_block = source.split(".combat-action-panel {", maxsplit=1)[1].split(".combat-action-panel .combat-token-strip", maxsplit=1)[0]
    assert "button-surface-03-aged-bronze.webp" not in action_panel_block
    token_block = source.split(".combat-token {", maxsplit=1)[1].split(".combat-token img", maxsplit=1)[0]
    assert "button-surface-03-aged-bronze.webp" not in token_block
    assert "duel-hall.webp" in source
    assert "universal-combat-bg.webp" in source
    assert ".combat-log-icon" in source
    assert ".combat-exchange-wave" in source
    assert ".combat-exchange-wave__line" in source
    assert "grid-auto-rows: min-content;" in actions
    assert ".combat-exchange-wave__line .combat-log-facts" in actions
    assert ".combat-battle-log" in source
    assert ".combat-log-panel--embedded" in source
    assert ".combat-battle-log {\n    min-width: 0;\n    min-height: 0;\n    height: 100%;" in source
    assert ".combat-log-panel--embedded .combat-log-list {\n    height: 100%;\n    max-height: none;" in source
    assert "font-size: 10px;" in logs
    assert "font-size: 9px;" in logs
    assert "@media (min-width: 768px)" in source
    assert "@media (min-width: 1025px)" in source
    assert ".combat-field > .combat-field-actor--hero" in source
    assert ".combat-field > .combat-field-actor--enemy {\n        display: none;" in responsive
    assert "grid-template-rows: minmax(0, 1fr);" in responsive
    assert ".combat-field-actor--enemy .combat-field-portrait {\n    order: 2;" in source
    assert ".combat-field-actor--enemy .combat-field-portrait {\n        order: 0;" not in source
    assert ".combat-field-actor--enemy .combat-resource span,\n    .combat-field-actor--enemy .combat-resource i,\n    .combat-field-actor--enemy .combat-resource strong {\n        order: initial;" not in source
    assert ".combat-effect-empty" in source
    assert ".combat-header-panel-toggle" not in source
    assert ".combat-header-state" not in source
    assert "display: none;" in source
    assert "--center-content-max: 820px;" in source
    assert "grid-template-rows: auto minmax(0, 1fr) auto;" in source
    assert "align-content: stretch;" in source
    assert ".combat-statebar," in source
    assert "@media (max-width: 860px)" in source
    assert ".combat-statebar {\n        display: none;" in source
    assert "width: 100%;" in source
    assert "grid-template-rows: minmax(138px, auto) minmax(0, 1fr);" not in responsive
    assert "--combat-target-card-width: 100%;" in source
    assert "min-height: min(430px, calc(100dvh" not in responsive
    assert "grid-template-rows: auto 42px auto;" not in responsive
    assert "grid-template-rows: auto minmax(0, 1fr) auto;" in responsive
    assert ".combat-field > .combat-field-actor--enemy {\n        grid-row: 1;\n        align-self: start;" in responsive
    assert ".combat-field > .combat-field-actor--hero {\n        grid-row: 3;\n        align-self: end;" in responsive
    assert ".combat-field > .combat-exchange-card {\n        grid-row: 2;\n        align-self: center;\n        justify-self: center;" in responsive
    assert ".combat-exchange-trigger" in responsive
    assert ".combat-exchange-inline {\n        display: none;" in responsive
    assert ".combat-exchange-modal" in actions
    assert ".combat-exchange-wave__lines {\n        max-height: none;\n        overflow: visible;" in responsive
    assert ".combat-action-panel {\n        gap: 6px;\n        padding: 7px;\n        max-height: min(38dvh, 270px);" in responsive
    assert ".combat-feint-row {\n        grid-template-columns: 26px minmax(0, 1fr);" in responsive
    assert ".combat-feint-row--empty {\n        grid-template-columns: minmax(0, 1fr);" in responsive
    assert ".combat-feint-pin {\n        width: 26px;\n        min-height: 28px;\n        height: 28px;\n        aspect-ratio: auto;" in responsive
    assert ".combat-feint-option,\n    .combat-feint-option--debug {\n        min-height: 28px;\n        height: 28px;" in responsive
    assert ".combat-feint-row--empty .combat-feint-option--debug {\n        width: 100%;" in responsive
    assert ".combat-feint-option img,\n    .combat-feint-icon {\n        width: 12px;\n        height: 12px;" in responsive
    assert ".combat-feint-title {\n        -webkit-line-clamp: 1;" in responsive
    assert "--combat-target-card-width: clamp(340px, 52cqw, 620px);" in source
    assert "--combat-target-portrait-size: clamp(100px, min(16cqw, 30cqh), 190px);" in source
    assert "grid-template-columns: minmax(0, 1fr) var(--combat-target-portrait-size);" in source
    assert "width: var(--combat-target-portrait-size);" in source
    assert "height: var(--combat-target-portrait-size);" in source
    assert ".combat-action-panel {\n        align-self: end;" in source
    assert ".combat-commit-frame--committed" in source
    assert ".combat-commit-row--timeout_warning" in source
    assert ".combat-info-list" in source
    assert "grid-template-columns: minmax(0, 1fr);" in source
    assert ".combat-ability-strip" in actions
    assert "grid-template-columns: repeat(8, var(--combat-ability-slot-size));" in actions
    assert ".combat-ability-grid:has(> :nth-child(9))" in actions
    assert "--combat-ability-slot-size: 30px;" in actions
    assert ".combat-roster-group" in source
    assert ".combat-roster-group__head" in source
    assert ".combat-action-group--desktop" not in source
    assert ".combat-action-group--mobile" not in source
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in source
    assert ".combat-viewport" not in source
    assert "#center-screens" not in source
    assert "height: 100%;" in screen
    assert "grid-template-rows: auto minmax(0, 1fr) auto auto;" in screen
    assert ".combat-mobile-dock {\n        display: none;" in source
    assert ".combat-action-panel {\n        position: sticky;\n        bottom: 0;" not in source
    assert ".combat-action-panel {\n        max-height: min(44dvh, 320px);" in source
    assert ".combat-primary-row {\n        order: 3;" in source
    assert "position: sticky;\n        bottom: 0;" in source
    assert ".combat-primary-row {\n        order: -1;" not in source
    mobile_actions = actions.split("@media (max-width: 860px)", maxsplit=1)[1]
    assert ".combat-field {\n        min-height: auto;\n        grid-template-rows: auto minmax(0, 1fr) auto;\n        align-content: stretch;" in mobile_actions
    assert "minmax(240px, 1fr)" not in mobile_actions
    assert ".combat-exchange-card {\n        align-content: center;" in actions
    assert ".combat-ability-option--empty" in source
    assert "button-surface-02-blackened-metal.webp" in source
    assert ".combat-tool-panel {\n        order: -1;" not in source
    assert ".combat-decision-panel {\n        order: 1;" in source
    assert ".combat-refresh-button" in source


def test_combat_log_panel_renders_line_icons():
    template = Path("src/frontend/templates/game/domains/combat/viewport/log_panel.html").read_text()

    assert "combat-log-icon" in template
    assert "line.icon_url" in template
    assert "combat_log_panel_id" in template
    assert "panel_id={{ panel_id }}" in template
    assert "combat_log_show_size_control" in template
    assert "line_kind in ['result', 'death', 'log']" not in template


def test_combat_log_panel_renders_new_uppercase_event_types():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/combat/viewport/log_panel.html")
    hero_ref = CombatLogActorRefDTO(id="1", name="Hero", team="team_1")
    target_ref = CombatLogActorRefDTO(id="2", name="Shadow", team="team_2")

    html = template.render(
        char_id=1,
        combat_log_panel_id="combat-battle-log-panel",
        combat_log_label="BATTLE LOG",
        combat_log_embedded=True,
        combat_log_show_size_control=False,
        combat_log_turns=[
            CombatLogTurnDTO(
                global_turn=2,
                title="Ход 2",
                entries=[
                    CombatEventDTO(
                        type="HIT",
                        text="Hero lands a clean hit.",
                        source=hero_ref,
                        target=target_ref,
                        data={
                            "catalog": "combat_text",
                            "catalog_key": "combat.exchange.default.parry",
                            "catalog_tooltip": "description",
                        },
                    )
                ],
            )
        ],
        combat_log_entries=[],
        combat_log_page=1,
        combat_log_page_size=8,
        combat_log_total=1,
        combat_log_total_pages=1,
        combat_log_pages=[1],
    )

    assert "Hero lands a clean hit." in html
    assert "combat-log-line" in html
    assert "is-player-source" in html
    assert "data-catalog=" not in html
    assert "data-catalog-key=" not in html
    assert "data-catalog-tooltip" not in html


def test_combat_log_panel_renders_mechanical_facts_after_text():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/combat/viewport/log_panel.html")
    hero_ref = CombatLogActorRefDTO(id="1", name="CodexDLC", team="team_1")
    target_ref = CombatLogActorRefDTO(id="2", name="Shadow CodexDLC", team="team_2")

    html = template.render(
        char_id=1,
        combat_log_panel_id="combat-battle-log-panel",
        combat_log_label="BATTLE LOG",
        combat_log_embedded=True,
        combat_log_show_size_control=False,
        combat_log_turns=[
            CombatLogTurnDTO(
                global_turn=8,
                title="Ход 8",
                entries=[
                    CombatEventDTO(
                        type="COUNTER",
                        kind="COUNTER",
                        text="CodexDLC отвечает контратакой по Shadow CodexDLC.",
                        source=hero_ref,
                        target=target_ref,
                        resources=[
                            {
                                "actor_id": "2",
                                "resource": "hp",
                                "before": 33,
                                "after": 30,
                                "max": 56,
                                "delta": -3,
                                "label": "HP 30/56",
                            }
                        ],
                        effects=[
                            {
                                "actor_id": "2",
                                "owner": "target",
                                "effect_id": "dot_bleed",
                                "action": "applied",
                                "duration": 3,
                                "icon": "combat/effects/dot_bleed.svg",
                                "tooltip": "Кровотечение // осталось 3 хода",
                            }
                        ],
                        flags={"counter": True, "dodged": True, "crit": True},
                    )
                ],
            )
        ],
        combat_log_entries=[],
        combat_log_page=1,
        combat_log_page_size=8,
        combat_log_total=1,
        combat_log_total_pages=1,
        combat_log_pages=[1],
    )

    assert "CodexDLC отвечает контратакой по Shadow CodexDLC." in html
    assert "combat-log-facts" in html
    assert '<span class="combat-log-text">CodexDLC отвечает контратакой по Shadow CodexDLC.</span>' in html
    assert "[HP 30/56]" in html
    assert 'data-delta="-3"' in html
    assert "token-counter.svg" not in html
    assert "token-dodge.svg" in html
    assert "token-crit.svg" in html
    assert 'data-token="counter"' not in html
    assert 'data-token="dodge"' in html
    assert "[counter +1]" not in html
    assert "[dodge +1]" not in html
    assert "Кровотечение // осталось 3 хода" in html
    assert "bleeding.svg" in html
    assert "[dot_bleed 3]" not in html
    assert "[-3]" not in html
    assert "CodexDLC отвечает контратакой по Shadow CodexDLC.;" not in html


def test_combat_log_panel_presents_semicolon_glue_as_readable_text():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/combat/viewport/log_panel.html")

    html = template.render(
        char_id=1,
        combat_log_panel_id="combat-battle-log-panel",
        combat_log_label="BATTLE LOG",
        combat_log_embedded=True,
        combat_log_show_size_control=False,
        combat_log_turns=[
            CombatLogTurnDTO(
                global_turn=9,
                title="Ход 9",
                entries=[
                    CombatEventDTO(
                        type="DODGE",
                        kind="DODGE",
                        text=(
                            "CodexDLC коротко отступает, проводит короткий режущий удар "
                            "и ищет открытую сторону Shadow; но Shadow отшагивает с линии атаки."
                        ),
                    )
                ],
            )
        ],
        combat_log_entries=[],
        combat_log_page=1,
        combat_log_page_size=8,
        combat_log_total=1,
        combat_log_total_pages=1,
        combat_log_pages=[1],
    )

    assert "; но" not in html
    assert "Shadow, но Shadow отшагивает" in html


def test_combat_screen_vm_exposes_log_pagination_contract():
    screen = build_combat_screen_vm(
        CombatDashboardDTO(
            session_id="combat-1",
            turn_number=3,
            status="active",
            hero=CombatActorCardDTO(actor_id="1", name="Hero", team="team_1"),
            log_total=19,
        )
    )

    assert screen.log_page == 1
    assert screen.log_page_size == 8
    assert screen.log_total_pages == 3
    assert screen.log_pages == [1, 2, 3]


def test_combat_screen_vm_embedded_log_keeps_latest_eight_turns_when_backend_returns_newest_first():
    screen = build_combat_screen_vm(
        CombatDashboardDTO(
            session_id="combat-1",
            turn_number=12,
            status="active",
            hero=CombatActorCardDTO(actor_id="1", name="Hero", team="team_1"),
            events_delta=CombatDeltaDTO(
                turns=[
                    CombatLogTurnDTO(
                        global_turn=turn,
                        title=f"Ход {turn}",
                        entries=[
                            CombatEventDTO(
                                type="RESULT",
                                text=f"Turn {turn} exchange",
                                global_turn=turn,
                            )
                        ],
                    )
                    for turn in range(12, 0, -1)
                ]
            ),
            log_total=12,
        )
    )

    assert [turn.global_turn for turn in screen.log_turns] == [12, 11, 10, 9, 8, 7, 6, 5]
    assert [turn.lines[0].text for turn in screen.log_turns] == [
        "Turn 12 exchange",
        "Turn 11 exchange",
        "Turn 10 exchange",
        "Turn 9 exchange",
        "Turn 8 exchange",
        "Turn 7 exchange",
        "Turn 6 exchange",
        "Turn 5 exchange",
    ]


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
    assert "SUMMARY" in html
    assert "LOG" in html
    assert "ПОЛУЧЕНО ОПЫТА ВСЕГО" in html
    assert "НАВЫКИ НЕ ИЗМЕНИЛИСЬ" in html
    assert "LAST TURN" not in html
    assert "OUTCOME" not in html
    assert 'hx-post="/game/combat/result/continue"' in html
    assert 'hx-target="#game-session-root"' in html
    assert 'hx-swap="outerHTML"' in html
    assert 'hx-vals=\'{"char_id": 5}\'' in html
    assert 'data-target-state="exploration"' in html


def test_combat_spectating_template_renders_outcome_shell_with_refresh_and_log_tab():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/combat/viewport/main.html")
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=3,
        status="spectating",
        battle_type="shadow",
        hero=CombatActorCardDTO(
            actor_id="5",
            name="Hero",
            team="team_1",
            is_dead=True,
            vitals=CombatActorVitalsDTO(hp_current=0, hp_max=63),
        ),
        allies=[
            CombatActorCardDTO(
                actor_id="6",
                name="Ally",
                team="team_1",
                vitals=CombatActorVitalsDTO(hp_current=18, hp_max=30),
            )
        ],
        enemies=[
            CombatActorCardDTO(
                actor_id="9",
                name="Shadow Hero",
                team="team_2",
                vitals=CombatActorVitalsDTO(hp_current=25, hp_max=40),
            )
        ],
    )

    html = template.render(
        char_id=5,
        combat=dashboard,
        combat_screen=build_combat_screen_vm(dashboard),
        combat_outcome_screen=build_combat_outcome_screen_from_dashboard_vm(dashboard),
    )

    assert "Ты пал" in html
    assert "Бой продолжается" in html
    assert "SUMMARY" in html
    assert "LOG" in html
    assert "Обновить статус боя" in html
    assert 'hx-get="/game/session/state/combats?char_id=5"' in html
    assert "htmx.ajax('GET', '/game/combat/logs?char_id=5&page=1&page_size=8&panel_id=combat-outcome-log-panel&embedded=1'" in html
    assert "ПОЛУЧЕНО ОПЫТА ВСЕГО" not in html
    assert "ИТОГ БОЯ ЕЩЕ НЕ ОПРЕДЕЛЕН" in html


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
    assert "combat-result-defeat.webp" in right_html
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
            ),
            CombatActorCardDTO(
                actor_id="3",
                name="Third Force",
                team="team_3",
                vitals=CombatActorVitalsDTO(hp_current=25, hp_max=50),
            ),
        ],
    )

    screen = build_combat_screen_vm(dashboard)

    assert [actor.actor_id for actor in screen.allies] == ["1"]
    assert screen.allied_team.hp_current == 70
    assert screen.allied_team.hp_max == 100
    assert screen.enemy_team.hp_current == 65
    assert screen.enemy_team.hp_max == 130
    assert screen.allied_team.target_queue_size == 0
    assert screen.enemy_team.pending_action_count == 0
    assert [actor.team for actor in screen.enemies] == ["team_2", "team_3"]
    assert screen.enemies[0].avatar_url
    assert screen.enemies[0].vitals.hp_current == 40
    assert screen.enemies[0].vitals.energy_max == 1
    assert [group.team for group in screen.enemy_groups] == ["team_2", "team_3"]
    assert [group.label for group in screen.enemy_groups] == ["TEAM 2", "TEAM 3"]
    assert [row.actor_id for row in screen.enemy_groups[0].rows] == ["2"]
    assert [row.actor_id for row in screen.enemy_groups[1].rows] == ["3"]


def test_combat_vm_exposes_full_token_strip_from_backend_key_values():
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=3,
        status="active",
        hero=CombatActorCardDTO(
            actor_id="1",
            name="Hero",
            team="team_1",
            tokens={"hit": 2, "blood": 1, "gift": 1},
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
        "pressure",
        "blood",
        "gift",
    ]
    assert [token.value for token in screen.token_bar] == [0, 2, 0, 0, 0, 0, 0, 1, 1]
    assert screen.token_bar[1].icon_url.endswith("/token-hit.svg")
    assert screen.token_bar[-3].icon_url.endswith("/token-pressure.svg")
    assert screen.token_bar[-2].icon_url.endswith("/token-blood.svg")
    assert screen.token_bar[-1].icon_url.endswith("/token-gift.svg")
    assert screen.token_bar[0].catalog == "combat_tokens"
    assert screen.token_bar[0].catalog_key == "tempo"


def test_combat_vm_uses_physical_icons_for_basic_ability_slots_only():
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
        available_actions=[
            CombatActionOptionDTO(
                action="instant",
                label="Кровавый голод",
                enabled=True,
                target_id="1",
                ability_id="basic_blood_hunger",
            ),
            CombatActionOptionDTO(
                action="instant",
                label="Рассечь даром",
                enabled=True,
                target_id="2",
                ability_id="basic_cleave_gift",
            ),
            CombatActionOptionDTO(
                action="instant",
                label="Слабое место",
                enabled=True,
                target_id="2",
                ability_id="basic_expose_weakness",
            ),
            CombatActionOptionDTO(
                action="instant",
                label="Скользнуть сквозь боль",
                enabled=True,
                target_id="1",
                ability_id="basic_slip_pain",
            ),
            CombatActionOptionDTO(
                action="instant",
                label="Сбить стойку",
                enabled=True,
                target_id="2",
                ability_id="basic_break_stance",
            ),
            CombatActionOptionDTO(
                action="instant",
                label="Сколочный удар",
                enabled=True,
                target_id="2",
                ability_id="basic_splinter_strike",
            ),
            CombatActionOptionDTO(
                action="instant",
                label="Стереть кровь",
                enabled=True,
                target_id="1",
                ability_id="basic_wipe_blood",
            ),
            CombatActionOptionDTO(
                action="instant",
                label="Последний рывок",
                enabled=True,
                target_id="1",
                ability_id="basic_last_push",
            ),
            CombatActionOptionDTO(
                action="instant",
                label="Огненный шар",
                enabled=True,
                target_id="2",
                ability_id="fireball",
            ),
        ],
    )

    screen = build_combat_screen_vm(dashboard)

    icons = {action.ability_id: action.icon_url for action in screen.ability_options}
    assert icons["basic_break_stance"].endswith("/abilities/basic_break_stance.svg")
    assert icons["basic_expose_weakness"].endswith("/abilities/basic_expose_weakness.svg")
    assert icons["basic_splinter_strike"].endswith("/abilities/basic_splinter_strike.svg")
    assert icons["basic_cleave_gift"].endswith("/abilities/basic_cleave_gift.svg")
    assert icons["basic_wipe_blood"].endswith("/abilities/basic_wipe_blood.svg")
    assert icons["basic_slip_pain"].endswith("/abilities/basic_slip_pain.svg")
    assert icons["basic_last_push"].endswith("/abilities/basic_last_push.svg")
    assert icons["basic_blood_hunger"].endswith("/abilities/basic_blood_hunger.svg")
    assert icons["fireball"].endswith("/gift-token.svg")
    assert [action.ability_id for action in screen.ability_options[:8]] == [
        "basic_break_stance",
        "basic_expose_weakness",
        "basic_splinter_strike",
        "basic_cleave_gift",
        "basic_wipe_blood",
        "basic_slip_pain",
        "basic_last_push",
        "basic_blood_hunger",
    ]


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


def test_combat_vm_reactive_effect_badge_uses_event_duration_label():
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
                CombatEffectBadgeDTO(
                    effect_id="prep_parry_riposte",
                    expires_at_exchange=1004,
                    title="Готовый рипост",
                    description="Следующее успешное парирование получает повышенный шанс контратаки.",
                    duration_label="до следующего парирования",
                ),
            ],
        ),
    )

    screen = build_combat_screen_vm(dashboard)

    effect = screen.hero.effects[0]
    assert effect.duration_text is None
    assert effect.title == "Готовый рипост"
    assert effect.description == "Следующее успешное парирование получает повышенный шанс контратаки."
    assert effect.tooltip == (
        "Готовый рипост // до следующего парирования // "
        "Следующее успешное парирование получает повышенный шанс контратаки."
    )


def test_combat_vm_ranged_position_badge_exposes_current_position():
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
                CombatEffectBadgeDTO(
                    effect_id="ranged_position",
                    expires_at_exchange=7,
                    params={"position": "close"},
                ),
            ],
        ),
    )

    screen = build_combat_screen_vm(dashboard)

    effect = screen.hero.effects[0]
    assert effect.icon_url.endswith("/ranged_position.svg")
    assert effect.duration_text is None
    assert effect.label_text == "CLOSE"
    assert effect.title == "Дистанция лучника: ближняя"
    assert "урон -30%" in effect.tooltip
    assert "Входящий ближний урон +30%" in effect.tooltip


def test_combat_effect_badges_render_icons_and_position_labels():
    template = Path("src/frontend/templates/game/domains/combat/left_sidebar/main.html").read_text(encoding="utf-8")
    right_sidebar = Path("src/frontend/templates/game/domains/combat/right_sidebar/main.html").read_text(encoding="utf-8")
    viewport = Path("src/frontend/templates/game/domains/combat/viewport/main.html").read_text(encoding="utf-8")
    css = Path("src/frontend/static/css/game/domains/combat/sidebars.css").read_text(encoding="utf-8")

    assert "combat-effect-mark" not in template
    assert "combat-effect-mark" not in right_sidebar
    assert "combat-effect-mark" not in viewport
    assert '<img src="{{ effect.icon_url }}"' in template
    assert '<img src="{{ effect.icon_url }}"' in right_sidebar
    assert '<img src="{{ effect.icon_url }}"' in viewport
    assert "{% if effect.label_text %}" in template
    assert "{% if effect.label_text %}" in right_sidebar
    assert "{% if effect.label_text %}" in viewport
    assert ".combat-effect--effect" in css
    assert '.combat-effect[data-catalog-key="ranged_position"]' in css
    assert ".combat-effect-stack--field" in css


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
    assert screen.feint_options[0].cost_tooltip == "Стоимость: HIT x2"


def test_combat_vm_disables_feint_when_concentration_is_too_low():
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=3,
        status="active",
        hero=CombatActorCardDTO(
            actor_id="1",
            name="Hero",
            team="team_1",
            vitals=CombatActorVitalsDTO(stamina_current=5, stamina_max=100),
            feints=[CombatFeintOptionDTO(feint_id="true_strike", cost={"hit": 2})],
        ),
        available_actions=[
            CombatActionOptionDTO(action="exchange", label="Атака", enabled=True, target_id="2"),
        ],
    )

    screen = build_combat_screen_vm(dashboard)

    assert screen.feint_options[0].enabled is False
    assert screen.feint_options[0].reason == "CONC 5/6"


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
                        "catalog": "combat_text",
                        "catalog_key": "combat.feint.true_strike.hit.humanoid_to_humanoid.weapon",
                        "catalog_event": "hit",
                        "catalog_taxonomy": "humanoid_to_humanoid",
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
                                "catalog": "combat_text",
                                "catalog_key": "combat.feint.true_strike.hit.humanoid_to_humanoid.weapon",
                            },
                        )
                    ],
                )
            ],
        ),
    )

    screen = build_combat_screen_vm(dashboard)

    assert screen.log_lines[0].catalog == "combat_text"
    assert screen.log_lines[0].global_turn == 7
    assert screen.log_lines[0].catalog_key == "combat.feint.true_strike.hit.humanoid_to_humanoid.weapon"
    assert screen.log_lines[0].catalog_event == "hit"
    assert screen.log_lines[0].catalog_tooltip == "description"
    assert screen.log_lines[0].icon_url is not None
    assert screen.log_lines[0].icon_url.endswith("/feint.svg")
    assert screen.log_turns[0].global_turn == 7
    assert screen.log_turns[0].title == "Ход 7"
    assert screen.log_turns[0].lines[0].catalog_key == "combat.feint.true_strike.hit.humanoid_to_humanoid.weapon"
    assert screen.log_turns[0].lines[0].icon_url is not None
    assert screen.log_turns[0].lines[0].icon_url.endswith("/feint.svg")


def test_combat_vm_renders_technical_log_effect_ids_as_effect_facts():
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=3,
        status="active",
        hero=CombatActorCardDTO(actor_id="1", name="CodexEN", team="team_1"),
        events_delta=CombatDeltaDTO(
            events=[
                CombatEventDTO(
                    type="HIT",
                    text="goblin_slinger выводит тетиву и стреляет в CodexEN. [marker_evasion] [ranged_position 1]",
                    source=CombatLogActorRefDTO(id="goblin_slinger", name="goblin_slinger", team="team_2"),
                    effects=[
                        {"effect_id": "marker_evasion", "label": "marker_evasion"},
                        {"effect_id": "ranged_position", "label": "ranged_position", "duration": 1},
                    ],
                    data={"global_turn": 7},
                )
            ]
        ),
    )

    screen = build_combat_screen_vm(dashboard)

    line = screen.log_lines[0]
    assert "goblin_slinger" not in line.text
    assert "гоблин-лучник" in line.text
    assert "marker_evasion" not in line.text
    assert "ranged_position" not in line.text
    assert line.source is not None
    assert line.source["name"] == "гоблин-лучник"
    assert line.effects == [
        {
            "effect_id": "marker_evasion",
            "label": "Уворот",
            "title": "Метка уворота",
            "tooltip": "Событие уворота: цель получила защитный маркер этого размена.",
            "icon": "/static/images/ui/combat-icons/token-dodge.svg",
        },
        {
            "effect_id": "ranged_position",
            "label": "Дистанция",
            "title": "Дистанция лучника",
            "tooltip": "Дальняя позиция повлияла на точность, урон или входящий ближний удар.",
            "icon": "/static/images/ui/combat-icons/ranged_position.svg",
            "duration": 1,
        },
    ]


def test_combat_vm_exposes_exchange_state():
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=3,
        status="active",
        hero=CombatActorCardDTO(actor_id="1", name="Hero", team="team_1"),
        exchange_state=CombatExchangeStateDTO(
            pair_status="ready_to_resolve",
            opponent_response_state="responded",
            title="PAIR READY",
            summary_text="Ответ противника получен.",
            turn=3,
        ),
    )

    screen = build_combat_screen_vm(dashboard)

    assert screen.exchange_state.pair_status == "ready_to_resolve"
    assert screen.exchange_state.opponent_response_state == "responded"
    assert screen.exchange_state.summary_text == "Ответ противника получен."


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


def test_combat_outcome_result_vm_matches_final_result_payload():
    result = CombatResultDTO(
        combat_id="combat-1",
        char_id=7,
        status="finished",
        outcome="victory",
        title="Победа",
        message="Бой завершен.",
        summary="Ваша команда победила.",
        reason="combat_session_finished",
        archived=True,
        teams={"team_1": ["7"], "team_2": ["-7"]},
        actors={
            "7": {"name": "Hero", "team": "team_1", "vitals_final": {"hp": 25, "max_hp": 40}},
            "-7": {"name": "Shadow", "team": "team_2", "is_dead": True, "vitals_final": {"hp": 0, "max_hp": 40}},
        },
        report={"last_turn": 9, "turns": 4},
        rewards={"progression": {"skill_swords": 0.0003}},
        metadata={"battle_type": "arena"},
        primary_action=CombatResultActionDTO(label="Продолжить", target_state="arena"),
    )

    screen = build_combat_outcome_screen_from_result_vm(result)

    assert screen.mode == "final"
    assert screen.title == "Победа"
    assert screen.last_turn == 9
    assert screen.primary_label == "Продолжить"
    assert screen.primary_action_kind == "continue"
    assert screen.primary_target_state == "arena"


def test_combat_outcome_spectating_vm_uses_refresh_action_and_current_teams():
    dashboard = CombatDashboardDTO(
        session_id="combat-1",
        turn_number=3,
        status="spectating",
        battle_type="shadow",
        hero=CombatActorCardDTO(
            actor_id="1",
            name="Hero",
            team="team_1",
            is_dead=True,
            vitals=CombatActorVitalsDTO(hp_current=0, hp_max=63),
        ),
        allies=[
            CombatActorCardDTO(
                actor_id="2",
                name="Ally",
                team="team_1",
                vitals=CombatActorVitalsDTO(hp_current=15, hp_max=30),
            )
        ],
        enemies=[
            CombatActorCardDTO(
                actor_id="3",
                name="Enemy",
                team="team_2",
                vitals=CombatActorVitalsDTO(hp_current=40, hp_max=50),
            )
        ],
    )

    screen = build_combat_outcome_screen_from_dashboard_vm(dashboard)

    assert screen is not None
    assert screen.mode == "spectating"
    assert screen.message == "Бой продолжается"
    assert screen.primary_label == "Обновить статус боя"
    assert screen.primary_action_kind == "refresh_status"
    assert screen.teams[0].alive_count == 1
    assert screen.teams[0].total_count == 2
    assert screen.teams[1].team == "team_2"


def test_combat_result_vm_builds_standard_combat_sidebars_from_finalization():
    result = CombatResultDTO(
        combat_id="combat-1",
        char_id=7,
        status="finished",
        outcome="victory",
        teams={"team_1": ["7"], "team_2": ["-7"], "team_3": ["-8"]},
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
            "-8": {
                "name": "Third Warband",
                "team": "team_3",
                "actor_type": "monster",
                "vitals_final": {"hp": 11, "max_hp": 30},
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
    assert screen.enemy_team.alive_count == 1
    assert screen.enemy_team.total_count == 2
    assert [enemy.actor_id for enemy in screen.enemies] == ["-7", "-8"]
    assert [group.team for group in screen.enemy_groups] == ["team_2", "team_3"]
    assert [row.actor_id for row in screen.enemy_groups[0].rows] == ["-7"]
    assert [row.actor_id for row in screen.enemy_groups[1].rows] == ["-8"]


def test_combat_screen_vm_uses_shadow_actor_avatar_before_shadow_fallback():
    dashboard = CombatDashboardDTO(
        session_id="combat-shadow",
        turn_number=1,
        status="active",
        hero=CombatActorCardDTO(
            actor_id="7",
            name="CodexDLC",
            actor_type="player",
            team="team_1",
            avatar_url="/static/images/avatars/rook7.webp",
            vitals=CombatActorVitalsDTO(hp_current=40, hp_max=40),
        ),
        target=CombatActorCardDTO(
            actor_id="-7",
            name="Shadow CodexDLC",
            actor_type="shadow",
            team="team_2",
            avatar_url="/static/images/avatars/rook7.webp",
            vitals=CombatActorVitalsDTO(hp_current=40, hp_max=40),
        ),
    )

    screen = build_combat_screen_vm(dashboard)

    assert screen.target is not None
    assert screen.target.is_shadow is True
    assert screen.target.avatar_url == "/static/images/avatars/rook7.webp"

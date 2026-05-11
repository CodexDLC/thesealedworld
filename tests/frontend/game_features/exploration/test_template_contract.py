from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.frontend.game_features.inventory.view_models.window import (
    InventoryRowVM,
    build_inventory_card_vm,
    build_inventory_window_vm,
    inventory_card_class,
    inventory_card_dimensions,
)
from src.shared.schemas.inventory import InventoryWindowDTO


def test_exploration_center_template_has_navigation_and_encounter_surfaces():
    template = Path("src/frontend/templates/game/domains/exploration/viewport/main.html").read_text()

    assert "payload_type == 'exploration_encounter'" in template
    assert "/game/exploration/move" in template
    assert "/game/exploration/interact" in template
    assert "exploration-control-panel" in template
    assert "exploration.navigation" in template
    assert "data-move-duration" in template
    assert "exploration-move-cooldown" in template
    assert "game/domains/exploration/right_sidebar/main.html" in template
    assert "hx-swap-oob=\"true\"" in template
    assert "AUTO ROUTES" in template
    assert "MOVE NORTH" in template
    assert "service_card(service)" in template
    assert "game/domains/exploration/components/services.html" in template
    assert "SERVICE_PENDING" not in template
    assert "exploration_button(exploration.grid.ne" not in template
    assert "exploration_button(exploration.grid.sw" not in template
    assert "exploration_button(exploration.grid.se" not in template
    assert "PEOPLE" not in template
    assert "exploration.hud.threat if exploration.hud.threat is defined else 0" in template
    assert "T{{ exploration.hud.threat_tier" in template


def test_exploration_right_sidebar_has_navigation_and_encounter_contexts():
    template = Path("src/frontend/templates/game/domains/exploration/right_sidebar/main.html").read_text()

    assert "payload_type == 'exploration_navigation'" in template
    assert "payload_type == 'exploration_encounter'" in template
    assert "LOCAL_CONTEXT" in template
    assert "service_card(service, compact=true)" in template
    assert "exploration.hud.threat if exploration.hud.threat is defined else 0" in template
    assert "<span>TIER</span>" in template


def test_exploration_service_component_has_default_icon_mapping():
    template = Path("src/frontend/templates/game/domains/exploration/components/services.html").read_text()

    assert "service_icon_url" in template
    assert "service-icons/blacksmith.svg" in template
    assert "service-icons/default.svg" in template
    assert "service-card-action" in template
    assert "/game/exploration/use-service" in template
    assert '"service_id"' in template


def test_arena_main_template_has_service_lobby_contract():
    template = Path("src/frontend/templates/game/domains/arena/viewport/main.html").read_text()

    assert "arena_screen == 'main_menu'" in template
    assert "arena-header-art" in template
    assert "arena-mode-grid" in template
    assert "arena-mode-card--duel" in template
    assert "arena-mode-card--group" in template
    assert "arena-mode-stage" in template
    assert "arena-queue-card" in template
    assert "arena-duel-ranked-grid" in template
    assert "arena-search-limit" in template
    assert "arena-group-plans" in template
    assert "arena-group-tabs" in template
    assert "arena_group_browser" in template
    assert "/game/arena/group-action" in template
    assert "arena-live-battles" in template
    assert "arena-battle-row" in template
    assert "arena-matchmaking-panel" in template
    assert "arena-search-stage" in template
    assert "arena-service-exit" in template
    assert "status_seed.symbiote_name" in template
    assert "symbiote-readout-name" in template
    assert "NO_DATA" in template
    assert "/game/arena/action" in template


def test_arena_right_sidebar_has_view_contract():
    shell = Path("src/frontend/templates/game/session_content_inner.html").read_text()
    template = Path("src/frontend/templates/game/domains/arena/right_sidebar/main.html").read_text()

    assert "game/domains/arena/right_sidebar/main.html" in shell
    assert "ARENA_VIEW" in template
    assert "GEAR SCORE" in template
    assert "RANK" in template
    assert "HALLS" in template
    assert "LIVE BATTLES" not in template
    assert "NO_DATA" in template


def test_arena_group_action_modal_contract():
    template = Path("src/frontend/templates/game/domains/arena/fragments/group_action_modal.html").read_text()
    route = Path("src/frontend/game_features/arena/routes/actions.py").read_text()

    assert "game-modal-root" in template
    assert "arena-modal-backdrop" in template
    assert "arena-dev-modal" in template
    assert "notice.get('formats'" in template
    assert "/game/arena/group-action" in route
    assert "service.group_action" in route


def test_arena_css_is_a_dedicated_game_module():
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text()
    source = Path("src/frontend/static/css/pages/game/arena.css").read_text()

    assert '@import url("pages/game/arena.css");' in bundle
    assert ".arena-lobby" in source
    assert "#arena-poll-region" in source
    assert ".arena-header-art" in source
    assert ".arena-mode-stage" in source
    assert ".arena-queue-card" in source
    assert ".arena-duel-ranked-grid" in source
    assert ".arena-search-limit" in source
    assert ".arena-group-plans" in source
    assert ".arena-group-tabs" in source
    assert ".arena-plan-card" in source
    assert ".arena-modal-backdrop" in source
    assert ".arena-live-battles" in source
    assert ".arena-battle-row" in source
    assert ".arena-search-stage" in source
    assert ".arena-countdown-value" in source
    assert ".arena-view-stat-grid" in source
    assert "arena-icons/sword-clash.svg" in source
    assert "arena-icons/knight-banner.svg" in source
    assert "arena-icons/tattered-banner.svg" in source
    assert "arena-main-hub.webp" in source
    assert "duel-hall.webp" in source
    assert "team-battle-hall.webp" in source
    assert "queue-scanner.webp" in source
    assert "combat-pending-gate.webp" in source
    assert "button-surface-02-blackened-metal.webp" in source


def test_status_main_prefers_panel_renderer_before_legacy_fragments():
    template = Path("src/frontend/templates/game/components/status/main.html").read_text()

    assert "game/components/panel/main.html" in template
    assert "game/components/status/fragments/" in template
    assert template.index("game/components/panel/main.html") < template.index("game/components/status/fragments/")


def test_character_status_panel_header_can_refresh_itself():
    template = Path("src/frontend/templates/game/components/panel/main.html").read_text()

    assert "panel-refresh-button" in template
    assert 'hx-get="/game/character-status/panel?char_id={{ char_id }}"' in template
    assert 'hx-target="#status-container"' in template


def test_avatar_widget_marks_missing_resource_data_explicitly():
    template = Path("src/frontend/templates/game/components/panel/widgets/avatar.html").read_text()

    assert "DATA_MISSING" in template


def test_avatar_widget_renders_gear_score_corner():
    template = Path("src/frontend/templates/game/components/panel/widgets/avatar.html").read_text()

    assert "gear_score" in template
    assert ">GS<" in template


def test_status_attribute_and_skill_widgets_are_collapsible():
    attribute_template = Path("src/frontend/templates/game/components/panel/widgets/attribute_grid.html").read_text()
    skill_template = Path("src/frontend/templates/game/components/panel/widgets/skill_groups.html").read_text()

    for template in (attribute_template, skill_template):
        assert 'class="status-section status-section--collapsible"' in template
        assert 'class="sec status-section-toggle"' in template
        assert "status-section-toggle-icon" in template


def test_game_shell_has_inventory_hud_window_placeholder():
    template = Path("src/frontend/templates/game/base_game.html").read_text()

    assert "x-data='gameShell" in template
    assert "game-modal-root" in template
    assert "hud-window inventory-window" in template
    assert "windows.inventory.open" in template
    assert "windows.inventory.dragging" in template
    assert 'id="inventory-window-body"' in template
    assert "hud-window-drag-handle" in template
    assert "hud_window_resize_handles.html" in template
    assert "startHudWindowDrag('inventory'" in template
    assert 'game/components/inventory/window.html' in template


def test_inventory_window_template_defines_frontend_contract():
    template = Path("src/frontend/templates/game/components/inventory/window.html").read_text()

    assert "inventory.contract_state" in template
    assert "inventory-loadout" in template
    assert "inventory-doll" in template
    assert "inventory-accessories" in template
    assert "inventory-belt-slots" in template
    assert "is-locked" in template
    assert "accessory_slot_label_map" in template
    assert "inventory-accessory-row-label" in template
    assert "row.row_id != 'rings'" in template
    assert "inventory-accessory-row--{{ row.row_id }}" in template
    assert "'ring_1': 'Кольцо 1'" in template
    assert "'ring_2': 'Кольцо 2'" in template
    assert "'legs_garment': 'legwear'" in template
    assert "'feetwear': 'feetwear'" in template
    assert "weapon_icon_base_map" in template
    assert "'greatsword': 'weapon_two_hand'" in template
    assert "'dagger': 'weapon_dagger'" in template
    assert "'battle_axe': 'weapon_axe'" in template
    assert "slot.slot_id == 'two_hand'" in template
    assert "inventory-equip-zone--two-shadow" in template
    assert "inventory-tabs" in template
    assert "aria-selected" in template
    assert "inventory-search" in template
    assert "inventory.visible_cards" in template
    assert "inventory_cards[:inventory.rows_visible_count]" in template
    assert "data-inventory-cells" in template
    assert "inventory-container-status" in template
    assert "inventory-feedback" in template
    assert "inventory-tooltip-card" in template
    assert "inventory-equipped-icon" in template
    assert "inventory-grade-r" in template
    assert "inventory-gear/" in template
    assert "data-inventory-tooltip-trigger" in template
    assert "inventory-tooltip-template" in template
    assert "activeInventoryTab === 'resources'" in template
    assert "activeInventoryTab === 'quest'" in template
    assert "hoverRow" not in template
    assert 'hx-post="/game/inventory/action"' in template
    assert 'x-model.debounce.150ms="searchQuery"' in template
    assert "inventory_notice" in template
    assert "row.card_class" in template
    assert "row.comparison" in template
    assert "INVENTORY_LINK_PENDING" not in template


def test_inventory_window_template_renders_contract_view_model():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/components/inventory/window.html")

    html = template.render(inventory_window=build_inventory_window_vm({"avatar_url": "/avatar.png", "name": "Ada"}))

    assert 'data-contract-state="FRONTEND_CONTRACT_PENDING"' in html
    assert 'src="/avatar.png"' in html
    assert 'data-slot-id="chest_armor"' in html
    assert 'data-slot-id="chest_garment"' not in html
    assert 'data-slot-id="belt_accessory"' in html
    assert "NO_RUNTIME_ITEMS" not in html
    assert 'data-inventory-cells="50"' in html
    assert "Leather Bracers" not in html


def test_inventory_window_template_renders_backend_contract_dto():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/components/inventory/window.html")
    inventory = InventoryWindowDTO.model_validate(
        {
            "char_id": 7,
            "avatar_url": "/avatar.png",
            "avatar_name": "Ada",
            "stats": {"slots_total": 64, "slots_used": 8},
            "body_zones": [
                {
                    "zone_id": "chest",
                    "label": "Torso",
                    "position": "chest",
                    "primary_slot": {
                        "slot_id": "chest_armor",
                        "label": "Armor",
                        "layer": "armor",
                        "item": {
                            "item_id": "item-1",
                            "base_id": "leather_armor",
                            "item_type": "armor",
                            "placement": "equipped",
                            "name": "Leather Armor",
                        },
                    },
                }
            ],
            "weapon_slots": [
                {
                    "slot_id": "two_hand",
                    "label": "Two hand",
                    "layer": "equipment",
                    "item": {
                        "item_id": "item-3",
                        "base_id": "greatsword",
                        "item_type": "weapon",
                        "placement": "equipped",
                        "name": "Iron Greatsword",
                    },
                }
            ],
            "accessory_rows": [],
            "quick_slots": [{"slot_id": "belt_1", "slot_index": 1, "enabled": True}],
            "tabs": [{"tab_id": "items", "label": "Items", "icon": "I", "is_active": True}],
            "visible_rows": [
                {
                    "item_id": "item-2",
                    "icon": "B",
                    "name": "Bronze Sword",
                    "item_type": "weapon",
                    "quantity": 1,
                    "rarity": "shared",
                    "equip_target": "main_hand",
                    "details": {
                        "item_id": "item-2",
                        "name": "Bronze Sword",
                        "item_type": "weapon",
                        "rarity": "shared",
                        "details": [{"label": "Damage", "value": "+3", "tone": "positive"}],
                        "actions": [
                            {
                                "action": "equip",
                                "label": "Equip",
                                "slot_id": "main_hand",
                                "style": "primary",
                            }
                        ],
                    },
                }
            ],
        }
    )

    html = template.render(inventory_window=inventory)

    assert 'data-contract-state="SHARED_INVENTORY_CONTRACT_V1"' in html
    assert "x-data='{" in html
    assert '"activeInventoryTab": "items"' in html
    assert '"selectedSlot": null' in html
    assert '"inventoryNotice": ""' in html
    assert '"searchQuery": ""' in html
    assert 'inventoryNotice: "' not in html
    assert "Leather Armor" in html
    assert "Bronze Sword" in html
    assert "inventory-gear/weapon.svg" in html
    assert "inventory-equipped-icon" in html
    assert "inventory-grade-r0" in html
    assert 'hx-post="/game/inventory/action"' in html
    assert '"action": "unequip"' in html
    assert '"item_id": "item-1"' in html
    assert "Iron Greatsword" in html
    assert 'data-slot-id="two_hand-shadow"' in html
    assert '"item_id": "item-3"' in html
    assert '"slot_id": "two_hand"' in html
    assert '"action": "equip"' in html
    assert '"slot_id": "main_hand"' in html
    assert 'data-inventory-cells="64"' in html

    locked_html = template.render(
        inventory_window=inventory.model_copy(
            update={
                "can_act": False,
                "forbidden_reason": "Вы не можете пользоваться инвентарём сейчас.",
            }
        )
    )
    assert "inventoryNotice = &#34;\\u0412\\u044b" in locked_html
    assert "inventoryNotice = \"Вы не можете пользоваться инвентарём сейчас.\"" not in locked_html
    assert "&#34;Bronze Sword&#34;.toLowerCase()" in locked_html
    assert '|| "Bronze Sword".toLowerCase()' not in locked_html


def test_inventory_card_mapper_builds_grid_card_from_type_and_numeric_size():
    assert inventory_card_dimensions("armor", 0, 0) == (2, 2)
    assert inventory_card_dimensions("quest", 12, 7) == (8, 4)
    assert inventory_card_class("armor", 2, 2) == (
        "inventory-card--armor inventory-card--square inventory-card--medium inventory-card--2x2"
    )

    card = build_inventory_card_vm(
        InventoryRowVM(
            row_id="item-1",
            icon="A",
            name="Leather Bracers",
            item_type="armor",
            weight="1.2",
            quantity="1",
            rarity="common",
            equip_target="arms_armor",
            grid_w=0,
            grid_h=0,
            comparison=["Heat resist +5"],
        )
    )

    assert card.grid_w == 2
    assert card.grid_h == 2
    assert card.style == "--item-w: 2; --item-h: 2;"
    assert card.card_class == "inventory-card--armor inventory-card--square inventory-card--medium inventory-card--2x2"
    assert card.details == ["Тип: armor", "Вес: 1.2", "Кол-во: 1", "Грейд: common", "Heat resist +5"]


def test_inventory_css_has_loadout_container_and_table_contract():
    source = Path("src/frontend/static/css/components/inventory.css").read_text()
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text()
    legwear_icon = Path("src/frontend/static/images/ui/inventory-gear/legwear.svg")
    weapon_two_hand_icon = Path("src/frontend/static/images/ui/inventory-gear/weapon_two_hand.svg")

    assert ".inventory-loadout" in source
    assert ".inventory-equip-zone--head" in source
    assert ".inventory-equip-zone--outer" in source
    assert ".inventory-equip-zone--main { grid-column: 3; grid-row: 2; }" in source
    assert ".inventory-equip-zone--off { grid-column: 1; grid-row: 2; }" in source
    assert ".inventory-equip-zone--two" in source
    assert ".inventory-equip-zone--two { grid-column: 3; grid-row: 2; }" in source
    assert ".inventory-equip-zone--two-shadow { grid-column: 1; grid-row: 2; }" in source
    assert ".inventory-equip-zone--two-shadow .inventory-slot-title" in source
    assert "display: none" in source
    assert "grid-column: 1 / 4; grid-row: 2" not in source
    assert ".inventory-accessory-row--split" in source
    assert ".inventory-belt-slots" in source
    assert ".inventory-table-body" in source
    assert "flex: 1 1 auto" in source
    assert "--inventory-cell: var(--inventory-grid-base-cell)" in source
    assert "grid-auto-rows: var(--inventory-cell)" in source
    assert "grid-column: 1 / -1" in source
    assert "grid-row: span var(--inventory-grid-rows)" in source
    assert ".inventory-container-status" in source
    assert ".inventory-feedback" in source
    assert "scrollbar-width: none" in source
    assert "--inventory-grid-viewport-height" in source
    assert "height: var(--inventory-grid-height)" in source
    assert "--inventory-grid-cols: 8" in source
    assert "grid-template-columns: repeat(4, minmax(28px, 34px))" in source
    assert ".inventory-tooltip-card" in source
    assert ".inventory-tooltip-affix" in source
    assert ".inventory-tooltip-section-title" in source
    assert ".inventory-accessory-row-label" in source
    assert ".inventory-accessory-row--rings .inventory-accessory-slot" in source
    assert ".inventory-accessory-row--split .inventory-accessory-slot-label" in source
    assert ".inventory-tooltip-meta" in source
    assert ".inventory-equipped-icon" in source
    assert ".inventory-grade-r7" in source
    assert "--inventory-item-icon-url" in source
    assert "--inventory-tooltip-icon-url" in source
    assert "-webkit-mask" in source
    assert ".inventory-card--square" in source
    assert ".inventory-card--wide" in source
    assert "fabric_leather_02_diff_1k.webp" in source
    assert legwear_icon.exists()
    assert weapon_two_hand_icon.exists()
    assert '@import url("components/cards.css");' in bundle


def test_game_shell_drag_logic_lives_in_source_js():
    source = Path("src/frontend/static/js/core/game_shell.js").read_text()
    config = Path("src/frontend/static/css/compiler_config.json").read_text()

    assert "window.gameShell" in source
    assert "this.leftOpen && this.leftPanelView === nextView" in source
    assert "this.rightOpen && this.rightPanelView === nextView" in source
    assert "startHudWindowDrag" in source
    assert "startHudWindowResize" in source
    assert "resizeHudWindow" in source
    assert "moveHudWindow" in source
    assert "core/game_shell.js" in config


def test_inventory_frontend_route_proxies_actions_to_backend():
    route = Path("src/frontend/game_features/inventory/routes/fragments.py").read_text()
    client = Path("src/frontend/integrations/backend_api/inventory.py").read_text()

    assert '@router.post("/game/inventory/action"' in route
    assert "InventoryActionRequestDTO.model_validate" in route
    assert "inventory_api.action" in route
    assert "HTTP_409_CONFLICT" in route
    assert "async def action" in client
    assert '"/api/game/inventory/actions"' in client


def test_game_header_nav_marks_open_panels_and_windows_active():
    template = Path("src/frontend/templates/game/domains/game_menu/header_nav.html").read_text()

    assert "leftOpen && leftPanelView" in template
    assert "rightOpen && rightPanelView" in template
    assert "windows.{{ item.window }}.open" in template
    assert 'hx-get="/game/inventory/window?char_id={{ char_id }}"' in template
    assert 'hx-target="#inventory-window-body"' in template


def test_game_runtime_loads_before_alpine_initializes():
    template = Path("src/frontend/templates/game/base_game.html").read_text()

    assert template.index('/static/js/game.js') < template.index('/static/js/vendor/alpine.js')


def test_game_header_has_system_exit_to_lobby():
    template = Path("src/frontend/templates/game/includes/header.html").read_text()

    assert 'class="game-exit-link"' in template
    assert 'href="/game-lobby"' in template
    assert 'data-session-cleanup="pending"' in template

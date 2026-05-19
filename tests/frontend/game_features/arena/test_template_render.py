from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.backend.features.arena.resources import ArenaResources
from src.shared.schemas.arena import ArenaScreenEnum, ArenaUIPayloadDTO


def test_mode_menu_renders_queue_and_back_buttons_from_lowercase_actions():
    env = Environment(
        loader=FileSystemLoader("src/frontend/templates"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("game/domains/arena/viewport/main.html")
    arena = ArenaUIPayloadDTO(
        screen=ArenaScreenEnum.MODE_MENU,
        mode="one_vs_one",
        title="Схватка [1x1]",
        description="Описание",
        buttons=ArenaResources.get_mode_buttons("one_vs_one"),
        metadata={"queue_waiting_count": 2, "max_wait_limit_sec": 300},
    )

    rendered = template.render(
        arena=arena,
        char_id=7,
        status_seed=SimpleNamespace(symbiote_name="SYSTEM"),
    )

    assert "ArenaScreenEnum.MODE_MENU" not in rendered
    assert "arena-screen--mode_menu" in rendered
    assert "Искать противника" in rendered
    assert "Бой с тенью" in rendered
    assert "arena-queue-card--primary" in rendered
    assert "arena-queue-card--secondary" in rendered
    assert "arena-queue-meter--ranked" in rendered
    assert "arena-queue-meter--shadow" in rendered
    assert "arena-duel-ranked-grid" not in rendered
    assert "Отчет очереди" in rendered
    assert ">2 в поиске</strong>" in rendered
    assert "Бой найден" in rendered
    assert ">READY</strong>" in rendered
    assert "максимум 5 мин" in rendered
    assert rendered.count('type="button"') >= 4
    assert "Назад" in rendered
    assert "Текущие бои" in rendered
    assert "Смотреть" in rendered
    assert '"action": "join_queue"' in rendered
    assert '"wait_limit_sec"' not in rendered
    assert '"action": "start_shadow"' in rendered
    assert 'hx-target="#game-modal-root"' in rendered
    assert '"modal": true' in rendered
    assert '"action": "menu_main"' in rendered


def test_arena_viewport_renders_center_menu_inside_viewport():
    env = Environment(
        loader=FileSystemLoader("src/frontend/templates"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("game/domains/arena/viewport/main.html")
    arena = ArenaUIPayloadDTO(
        screen=ArenaScreenEnum.MAIN_MENU,
        mode="one_vs_one",
        title="Арена",
        description="Описание",
        buttons=ArenaResources.get_main_buttons(),
    )
    def nav_item(label, **overrides):
        values = {
            "label": label,
            "icon": "arena",
            "is_disabled": False,
            "is_active": False,
            "panel": None,
            "panel_view": None,
            "window": None,
            "modal": None,
            "url": None,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    nav = SimpleNamespace(
        l2=nav_item("STATUS", panel="left", panel_view="status"),
        l1=nav_item("QUESTS", modal="quests"),
        center=nav_item("ARENA", is_active=True),
        r1=nav_item("INVENTORY", panel="right", panel_view="inventory"),
        r2=nav_item("VIEW", panel="right", panel_view="context"),
    )

    rendered = template.render(
        arena=arena,
        char_id=7,
        nav=nav,
        status_seed=SimpleNamespace(symbiote_name="SYSTEM"),
    )

    assert "arena-center-menu" in rendered
    assert 'aria-label="Arena sections"' in rendered
    assert "dock-nav--five" in rendered
    assert ">QUESTS</span>" in rendered
    assert ">ARENA</span>" in rendered
    assert ">VIEW</span>" in rendered
    assert "$dispatch('game-modal-open', { kind: 'quests' })" in rendered
    assert "$dispatch('panel-toggle'" in rendered


def test_mode_menu_uses_static_card_icons_and_search_screen_keeps_scanner_animation():
    css = Path("src/frontend/static/css/game/domains/arena/matchmaking.css").read_text(encoding="utf-8")

    queue_meter_block = css.split(".arena-queue-meter {", maxsplit=1)[1].split("}", maxsplit=1)[0]
    search_orbit_block = css.split(".arena-search-orbit {", maxsplit=1)[1].split("}", maxsplit=1)[0]

    assert "animation:" not in queue_meter_block
    assert "arena-icons/sword-clash.svg" in css
    assert "arena-icons/knight-banner.svg" in css
    assert "animation: arena-queue-scan" in search_orbit_block


def test_searching_poll_uses_backend_action_values():
    env = Environment(
        loader=FileSystemLoader("src/frontend/templates"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("game/domains/arena/viewport/main.html")
    arena = ArenaUIPayloadDTO(
        screen=ArenaScreenEnum.SEARCHING,
        mode="one_vs_one",
        title="Поиск противника",
        description="Описание",
        buttons=ArenaResources.get_searching_buttons("one_vs_one"),
    )

    rendered = template.render(
        arena=arena,
        char_id=7,
        status_seed=SimpleNamespace(symbiote_name="SYSTEM"),
    )

    assert '"action": "check_match"' in rendered
    assert '"action": "CHECK_MATCH"' not in rendered
    assert 'id="arena-poll-region"' in rendered
    assert 'hx-target="#arena-poll-region"' in rendered
    assert 'hx-select="#arena-poll-region"' in rendered


def test_searching_screen_renders_wait_limit():
    env = Environment(
        loader=FileSystemLoader("src/frontend/templates"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("game/domains/arena/viewport/main.html")
    arena = ArenaUIPayloadDTO(
        screen=ArenaScreenEnum.SEARCHING,
        mode="one_vs_one",
        title="Поиск противника",
        description="Описание",
        wait_time_sec=7,
        buttons=ArenaResources.get_searching_buttons("one_vs_one"),
        metadata={"wait_limit_sec": 180, "queue_waiting_count": 4},
    )

    rendered = template.render(
        arena=arena,
        char_id=7,
        status_seed=SimpleNamespace(symbiote_name="SYSTEM"),
    )

    assert "Лимит ожидания" in rendered
    assert "3 мин" in rendered
    assert "В ожидании поиска" in rendered
    assert ">4</strong>" in rendered


def test_combat_pending_renders_confirmation_modal_without_scene_art():
    env = Environment(
        loader=FileSystemLoader("src/frontend/templates"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("game/domains/arena/viewport/main.html")
    arena = ArenaUIPayloadDTO(
        screen=ArenaScreenEnum.COMBAT_PENDING,
        mode="one_vs_one",
        title=ArenaResources.SHADOW_PENDING_TITLE,
        description=ArenaResources.SHADOW_PENDING_DESCRIPTION,
        buttons=ArenaResources.get_pending_buttons("one_vs_one", "arena-7"),
        wait_time_sec=9,
        arena_session_id="arena-7",
        metadata={"polling": True},
    )

    rendered = template.render(
        arena=arena,
        char_id=7,
        status_seed=SimpleNamespace(symbiote_name="SYSTEM"),
    )

    assert "arena-modal-backdrop--confirm" in rendered
    assert "arena-confirm-modal" in rendered
    assert 'role="dialog"' in rendered
    assert "Арена готова" in rendered
    assert "Тень материализована и готова вступить в бой." in rendered
    assert "Войти" in rendered
    assert "Отмена" in rendered
    assert '"action": "check_combat_ready"' in rendered
    assert '"action": "cancel_queue"' in rendered
    assert '"confirm": true' in rendered
    assert 'hx-target="#game-modal-root"' in rendered
    assert '"modal": true' in rendered
    assert "scene-img" not in rendered


def test_group_hall_renders_locked_lobby_and_future_intervention_browser():
    env = Environment(
        loader=FileSystemLoader("src/frontend/templates"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("game/domains/arena/viewport/main.html")
    arena = ArenaUIPayloadDTO(
        screen=ArenaScreenEnum.MODE_MENU,
        mode="group",
        title="Командные бои",
        description="Описание",
        buttons=ArenaResources.get_mode_buttons("group"),
        metadata={"group_lobby": ArenaResources.get_group_lobby_mock()},
    )

    rendered = template.render(
        arena=arena,
        char_id=7,
        status_seed=SimpleNamespace(symbiote_name="SYSTEM"),
    )

    assert "REMOTE WORKS" in rendered
    assert "Пока открыт только зал 1x1" in rendered
    assert "arena-repair-banner" in rendered
    assert "Ранговый бой" not in rendered
    assert "Создать заявку" not in rendered
    assert "arena-group-plans" not in rendered
    assert "arena-group-tabs" in rendered
    assert "Хаотические бои" in rendered
    assert "Групповые заявки" in rendered
    assert "/game/arena/group-action" in rendered
    assert "group_pick_team" in rendered
    assert "Текущие бои" in rendered
    assert "Вмешаться" in rendered
    assert "Смотреть" in rendered
    assert "Подбор недоступен" not in rendered


def test_arena_viewport_can_oob_refresh_right_sidebar():
    env = Environment(
        loader=FileSystemLoader("src/frontend/templates"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("game/domains/arena/viewport/main.html")
    arena = ArenaUIPayloadDTO(
        screen=ArenaScreenEnum.MODE_MENU,
        mode="one_vs_one",
        title="Схватка [1x1]",
        description="Описание",
        buttons=ArenaResources.get_mode_buttons("one_vs_one"),
        metadata={"rating": 1000, "rank": 1000, "league_name": "Bronze", "matches_played": 0, "placement_left": 5},
    )

    rendered = template.render(
        arena=arena,
        char_id=7,
        status_seed=SimpleNamespace(symbiote_name="SYSTEM"),
        oob_panels=True,
    )

    assert 'id="game-right-context-content"' in rendered
    assert 'hx-swap-oob="innerHTML"' in rendered
    assert "MMR" in rendered
    assert "1000" in rendered

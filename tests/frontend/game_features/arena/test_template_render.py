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
    )

    rendered = template.render(
        arena=arena,
        char_id=7,
        status_seed=SimpleNamespace(symbiote_name="SYSTEM"),
    )

    assert "ArenaScreenEnum.MODE_MENU" not in rendered
    assert "arena-screen--mode_menu" in rendered
    assert "Ранг 1 мин" in rendered
    assert "Ранг 3 мин" in rendered
    assert "Ранг 5 мин" in rendered
    assert "Бой с тенью" in rendered
    assert "arena-duel-ranked-grid" in rendered
    assert rendered.count('type="button"') >= 6
    assert "Назад" in rendered
    assert "Текущие бои" in rendered
    assert "Смотреть" in rendered
    assert '"action": "join_queue"' in rendered
    assert '"wait_limit_sec": 60' in rendered
    assert '"wait_limit_sec": 180' in rendered
    assert '"wait_limit_sec": 300' in rendered
    assert '"action": "start_shadow"' in rendered
    assert 'hx-target="#game-modal-root"' in rendered
    assert '"modal": true' in rendered
    assert '"action": "menu_main"' in rendered


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
        metadata={"wait_limit_sec": 180},
    )

    rendered = template.render(
        arena=arena,
        char_id=7,
        status_seed=SimpleNamespace(symbiote_name="SYSTEM"),
    )

    assert "Лимит ожидания" in rendered
    assert "3 мин" in rendered


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


def test_group_hall_renders_future_intervention_action():
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

    assert "Ранговый бой" in rendered
    assert "Создать заявку" in rendered
    assert "Потасовка" in rendered
    assert "arena-group-plans" in rendered
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

    assert 'id="game-right-content"' in rendered
    assert 'hx-swap-oob="innerHTML"' in rendered
    assert "MMR" in rendered
    assert "1000" in rendered

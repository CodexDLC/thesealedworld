import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.testclient import TestClient

from src.frontend.config.settings import settings
from src.frontend.core.database import get_db
from src.frontend.features.account.routes.pages import router
from src.frontend.integrations.backend_api.game_lobby import GameLobbyPayload, GameLobbyResponse, LobbySlotPayload
from src.shared.enums import CoreDomain
from src.shared.schemas import GameStateHeader


def _make_app(user=None):
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates

    from src.frontend.app import inline_css
    from src.frontend.config.settings import settings

    app = FastAPI()
    app.include_router(router)
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    templates.env.globals["inline_css"] = inline_css
    app.state.templates = templates

    async def _fake_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = _fake_db

    @app.middleware("http")
    async def inject_user(request, call_next):
        request.state.user = user
        request.state.game_menu_service = None
        return await call_next(request)

    return app


def _user_mock(*, tester_status="none", tester_approved_at=None):
    return MagicMock(
        id=uuid.uuid4(),
        email="test@example.com",
        is_active=True,
        is_superuser=False,
        tester_status=tester_status,
        tester_approved_at=tester_approved_at,
        referral_code="SEAL-TESTCODE",
        created_at=datetime(2026, 5, 1),
    )


def _patch_repo():
    mock_repo = AsyncMock()
    mock_repo.get_referral_stats = AsyncMock(return_value={"invited": 0, "active": 0, "bonus": 0})
    mock_repo.list_referrals = AsyncMock(return_value=[])
    return patch("src.frontend.features.account.routes.pages.UserRepository", return_value=mock_repo)


@pytest.mark.unit
class TestAccountRoutes:
    def test_account_redirects_to_profile(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/account", follow_redirects=False)
        assert response.status_code == 303
        assert "/account/profile" in response.headers["location"]

    def test_profile_page_returns_200_for_authenticated_user(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        with _patch_repo():
            response = client.get("/account/profile")
        assert response.status_code == 200
        assert "Мой аккаунт" in response.text
        assert "Персонажи" in response.text
        assert "Рефералы" in response.text
        assert "Платежи" in response.text
        assert "Подать заявку на тестирование" not in response.text
        assert "Хотите помочь с тестированием" not in response.text

    def test_profile_page_renders_selected_section_only(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        with _patch_repo():
            response = client.get("/account/profile?section=payments")
        assert response.status_code == 200
        assert "Платежи и донат" in response.text
        assert "Данные игрока" not in response.text
        assert 'section=payments" class="account-sidebar-link is-active"' in response.text

    def test_profile_page_falls_back_to_overview_for_unknown_section(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        with _patch_repo():
            response = client.get("/account/profile?section=unknown")
        assert response.status_code == 200
        assert "Личный кабинет" in response.text
        assert 'section=overview" class="account-sidebar-link is-active"' in response.text

    def test_characters_section_renders_character_summary_without_character_id(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        lobby_service = MagicMock()
        lobby_service.get_view = AsyncMock(
            return_value=GameLobbyResponse(
                header=GameStateHeader(current_state=CoreDomain.LOBBY),
                payload=GameLobbyPayload(
                    title="Порог",
                    description="Выбери персонажа.",
                    primary_action_label="Начать приключение",
                    primary_action="start_adventure",
                    max_slots=4,
                    slots=[
                        LobbySlotPayload(
                            index=1,
                            is_empty=False,
                            character_id="char-secret-42",
                            name="Prime Wanderer",
                            avatar_url="/static/images/avatars/silhouette_m.webp",
                            status="exploration",
                            presence_status="online",
                            location_id="52_52",
                            vitals={
                                "hp": {"current": 17, "max": 20},
                                "energy": {"current": 8, "max": 10},
                                "concentration": {"current": 6, "max": 9},
                            },
                            attributes={"strength": 9, "agility": 7, "endurance": 8},
                            equipped_items=[
                                {"name": "Rust Blade", "item_type": "weapon", "slot": "main_hand", "rarity": "shared"},
                                {"name": "Rust Shield", "item_type": "armor", "slot": "off_hand", "rarity": "shared"},
                                {"name": "Rust Mail", "item_type": "armor", "slot": "chest_armor", "rarity": "shared"},
                                {"name": "Rust Amulet", "item_type": "jewelry", "slot": "amulet", "rarity": "shared"},
                                {"name": "Rust Ring", "item_type": "jewelry", "slot": "ring", "rarity": "shared"},
                            ],
                            inventory_summary={"equipped_count": 1, "backpack_count": 2, "resource_count": 3},
                            skills=[{"skill_key": "skill_macing", "total_xp": 0.12, "is_unlocked": True}],
                        ),
                        LobbySlotPayload(index=2, is_empty=True, status="VACANT"),
                    ],
                ),
                payload_type="lobby_start",
            )
        )

        with (
            _patch_repo(),
            patch("src.frontend.features.account.routes.pages.get_game_lobby_page_service", return_value=lobby_service),
            patch.object(settings, "site_base_url", "http://thesealed.localhost:8080"),
            patch.object(settings, "play_public_base_url", "http://play.thesealed.localhost:8080"),
        ):
            response = client.get("/account/profile?section=characters")

        assert response.status_code == 200
        assert "Prime Wanderer" in response.text
        assert "17 / 20" in response.text
        assert "Энергия" in response.text
        assert "Концентрация" in response.text
        assert "Rust Blade" in response.text
        assert "Rust Ring" in response.text
        assert "Основная рука" in response.text
        assert "Ударное оружие" in response.text
        assert "12%" in response.text
        assert "Нет персонажа" in response.text
        lobby_href = "http://play.thesealed.localhost:8080/game-lobby"
        assert f'href="{lobby_href}?' in response.text
        assert 'href="/play"' not in response.text
        parsed_lobby_url = urlsplit(lobby_href + response.text.split(f'href="{lobby_href}', 1)[1].split('"', 1)[0])
        assert parse_qs(parsed_lobby_url.query) == {
            "return_to": ["http://thesealed.localhost:8080/account/profile?section=characters"]
        }
        assert "char-secret-42" not in response.text
        assert "main_hand" not in response.text
        assert "Skill Macing" not in response.text
        assert "12 XP" not in response.text
        assert "Подробнее" not in response.text

    def test_referrals_section_renders_referral_list_and_configured_site_url(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        mock_repo = AsyncMock()
        mock_repo.get_referral_stats = AsyncMock(return_value={"invited": 1, "active": 0, "bonus": 0})
        mock_repo.list_referrals = AsyncMock(
            return_value=[
                MagicMock(
                    email="friend@example.com",
                    created_at=datetime(2026, 6, 1),
                    email_verified_at=datetime(2026, 6, 2),
                )
            ]
        )

        with (
            patch("src.frontend.features.account.routes.pages.UserRepository", return_value=mock_repo),
            patch("src.frontend.features.account.routes.pages.settings.site_base_url", "https://thesealed.world"),
        ):
            response = client.get("/account/profile?section=referrals")

        assert response.status_code == 200
        assert "https://thesealed.world/register?ref=SEAL-TESTCODE" in response.text
        assert "fr***@example.com" in response.text
        assert "Подтверждён" in response.text
        assert "Приглашённый создал персонажа" in response.text
        assert "Не отслеживается" in response.text
        assert "PR-4" not in response.text

    def test_profile_page_redirects_anonymous_to_login(self):
        app = _make_app(user=None)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/account/profile", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers["location"]


@pytest.mark.unit
class TestApplyTesterRoute:
    @patch("src.frontend.features.account.routes.pages.get_db")
    def test_apply_tester_post_redirects_to_profile(self, mock_get_db):
        user = _user_mock(tester_status="none")
        app = _make_app(user=user)

        mock_session = AsyncMock()
        mock_get_db.return_value = mock_session

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_id.return_value = MagicMock(
            id=user.id, tester_status="none",
        )
        mock_repo_instance.update_tester_status = AsyncMock()
        mock_repo_instance.commit = AsyncMock()

        with patch(
            "src.frontend.features.account.routes.pages.UserRepository",
            return_value=mock_repo_instance,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/account/apply-tester", follow_redirects=False)

        assert response.status_code == 303
        assert "/account/profile" in response.headers["location"]

    def test_apply_tester_post_anonymous_redirects_to_login(self):
        app = _make_app(user=None)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/account/apply-tester", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers["location"]

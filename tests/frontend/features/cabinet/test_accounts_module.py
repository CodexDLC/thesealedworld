from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.frontend.features.cabinet.modules.accounts.cabinet as accounts
from fastapi_cabinet import include_cabinet
from src.frontend.cabinet import CABINET_MODULES
from src.frontend.features.cabinet.modules.accounts.cabinet import AccountsAdmin
from src.frontend.integrations.backend_api.admin_players import (
    AdminPlayerCharacterListResponse,
    AdminPlayerCharacterSummary,
    AdminPlayerGenerationClanOption,
    AdminPlayerGenerationOptionsResponse,
)


class _SessionContext:
    def __init__(self, session: object) -> None:
        self.session = session

    async def __aenter__(self) -> object:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeUserRepository:
    def __init__(self, session: object) -> None:
        self.session = session

    async def count_matching(self, query: str = "") -> int:
        assert query == "example"
        return 1

    async def list_page(self, *, limit: int, offset: int, query: str = "") -> list[object]:
        assert limit == 10
        assert offset == 0
        assert query == "example"
        return [_user()]

    async def get_by_id(self, user_id: UUID) -> object | None:
        assert user_id == UUID("11111111-1111-1111-1111-111111111111")
        return _user()


def test_accounts_admin_declares_read_surfaces_and_generation_action() -> None:
    assert AccountsAdmin.key == "accounts"
    assert AccountsAdmin.path == "/admin/accounts"
    assert AccountsAdmin.label == "Аккаунты"
    assert [item.key for item in AccountsAdmin.sidebar] == ["overview", "accounts"]
    assert AccountsAdmin.action_routes == {
        "browser": ("GET", "handle_browser"),
        "account-detail": ("GET", "handle_account_detail"),
        "character-detail": ("GET", "handle_character_detail"),
        "generate-character": ("POST", "handle_generate_character"),
    }


def test_accounts_custom_pages_render_read_only_browser() -> None:
    app = FastAPI()
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")
    client = TestClient(app)

    response = client.get("/admin/accounts/browser")

    assert response.status_code == 200
    assert "Аккаунты" in response.text
    assert "Email" in response.text
    assert "Применить" in response.text


def test_account_detail_renders_four_character_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAdminPlayersApi:
        async def list_user_characters(self, user_id: UUID, *, limit: int, offset: int):
            assert limit == 25
            assert offset == 0
            return AdminPlayerCharacterListResponse(
                user_id=user_id,
                total=1,
                limit=limit,
                offset=offset,
                items=[
                    AdminPlayerCharacterSummary(
                        character_id=7,
                        user_id=user_id,
                        name="Hero",
                        name_key="hero",
                        gender="other",
                        game_stage="lobby",
                        location_id="52_52",
                    )
                ],
            )

        async def list_character_generation_options(self):
            return AdminPlayerGenerationOptionsResponse(
                clans=[
                    AdminPlayerGenerationClanOption(
                        clan_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        label="Rust Cross / 50_52",
                        family_id="bandit_gang",
                        tier=2,
                    )
                ]
            )

    monkeypatch.setattr(accounts, "get_session_context", lambda: _SessionContext(object()))
    monkeypatch.setattr(accounts, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(accounts, "_api", lambda request: FakeAdminPlayersApi())
    app = FastAPI()
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")
    client = TestClient(app)

    response = client.get("/admin/accounts/account-detail?user_id=11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    assert "Слоты персонажей" in response.text
    assert "Hero" in response.text
    assert response.text.count("Пустой слот") == 3
    assert "Создать персонажа" in response.text
    assert "Сгенерированный клан" in response.text
    assert "Rust Cross / 50_52" in response.text


@pytest.mark.unit
async def test_account_browser_context_reads_site_users_with_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(accounts, "get_session_context", lambda: _SessionContext(object()))
    monkeypatch.setattr(accounts, "UserRepository", FakeUserRepository)
    request = SimpleNamespace(query_params={"q": "example", "limit": "10", "offset": "0"})

    browser = await accounts._load_account_browser_context(request)

    assert browser.error == ""
    assert browser.total == 1
    assert browser.limit == 10
    assert browser.accounts[0].email == "player@example.test"


def test_accounts_url_preserves_query_limit_and_offset() -> None:
    assert (
        accounts._accounts_url(query="player@example.test", limit=25, offset=50)
        == "/admin/accounts/browser?limit=25&offset=50&q=player%40example.test"
    )


def test_account_character_slots_keep_four_lobby_rows() -> None:
    character = AdminPlayerCharacterSummary(
        character_id=7,
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Hero",
        name_key="hero",
        gender="other",
        game_stage="lobby",
        location_id="52_52",
    )

    slots = accounts._account_character_slots([character], backend_available=True)

    assert len(slots) == 4
    assert slots[0].index == 1
    assert slots[0].character == character
    assert slots[0].action_enabled is True
    assert slots[1].state == "пустой"
    assert slots[1].action_label == "Создать персонажа"


def test_account_character_slots_mark_unknown_rows_when_backend_is_unavailable() -> None:
    slots = accounts._account_character_slots([], backend_available=False)

    assert len(slots) == 4
    assert all(slot.character is None for slot in slots)
    assert {slot.state for slot in slots} == {"не загружен"}
    assert {slot.action_label for slot in slots} == {"backend недоступен"}


def test_bounded_int_clamps_invalid_and_out_of_range_values() -> None:
    assert accounts._bounded_int("500", default=25, low=1, high=100) == 100
    assert accounts._bounded_int("-1", default=25, low=0, high=100) == 0
    assert accounts._bounded_int("bad", default=25, low=1, high=100) == 25


def _user() -> object:
    return SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        email="player@example.test",
        is_active=True,
        is_superuser=False,
        tester_status="approved",
        created_at=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
    )

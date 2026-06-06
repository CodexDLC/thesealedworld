"""Footer/hero/library stub render the release marker from settings."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_footer_shows_release_stage_and_version(client, monkeypatch) -> None:
    from src.frontend.config.settings import settings

    monkeypatch.setattr(settings, "release_stage", "alpha", raising=False)
    monkeypatch.setattr(settings, "release_version", "0.3.0", raising=False)

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert "build 0.3.0" in response.text
    assert "Альфа" in response.text
    assert "pre-alpha 0.1.0" not in response.text


@pytest.mark.unit
def test_landing_hero_chip_reflects_current_stage(client, monkeypatch) -> None:
    from src.frontend.config.settings import settings

    monkeypatch.setattr(settings, "release_stage", "alpha", raising=False)
    monkeypatch.setattr(settings, "release_version", "0.3.0", raising=False)

    response = client.get("/")
    assert response.status_code == 200
    # The hero kicker now reads from release_stage_label
    assert "Альфа · браузерная MMORPG" in response.text
    # The note line carries stage + build + anchor link
    assert 'href="#stages"' in response.text


@pytest.mark.unit
def test_landing_has_stages_section_with_progress_policy(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="stages"' in response.text
    assert "может быть сброшен" in response.text  # alpha policy text
    assert "Постоянный мир" in response.text  # release section copy


@pytest.mark.unit
def test_landing_stage_card_marks_active_stage(client, monkeypatch) -> None:
    from src.frontend.config.settings import settings

    monkeypatch.setattr(settings, "release_stage", "alpha", raising=False)
    response = client.get("/")
    assert response.status_code == 200
    # The alpha card has the is-active modifier
    assert "Этап · Альфа · сейчас" in response.text
    assert "Этап · Бета · сейчас" not in response.text
    assert "Этап · Релиз 1.0+ · сейчас" not in response.text


@pytest.mark.unit
def test_library_returns_maintenance_stub(client) -> None:
    response = client.get("/library")
    assert response.status_code == 200
    assert "Библиотека пересобирается" in response.text
    # The old shell (HTMX tree with Introduction / Monsters) is gone for now
    assert "library-tree" not in response.text


@pytest.mark.unit
def test_library_stub_shows_current_build(client, monkeypatch) -> None:
    from src.frontend.config.settings import settings

    monkeypatch.setattr(settings, "release_stage", "alpha", raising=False)
    monkeypatch.setattr(settings, "release_version", "0.3.0", raising=False)
    response = client.get("/library")
    assert "build 0.3.0" in response.text
    assert "Альфа" in response.text


@pytest.mark.unit
def test_library_internal_fragments_still_routable(client) -> None:
    """The HTMX fragment routes stay alive so the future restored shell can use
    them again without a route-table change."""
    response = client.get("/library/fragments/intro")
    assert response.status_code == 200

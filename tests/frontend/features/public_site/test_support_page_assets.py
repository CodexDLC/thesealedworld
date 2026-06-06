from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_support_page_assets_are_in_site_bundle() -> None:
    site_bundle = ROOT.joinpath("src/frontend/static/css/site_bundle.css").read_text(encoding="utf-8")
    compiler_config = ROOT.joinpath("src/frontend/static/css/compiler_config.json").read_text(encoding="utf-8")

    assert 'site/pages/support.css' in site_bundle
    assert 'site/support.js' in compiler_config


def test_support_page_is_linked_from_landing_and_header() -> None:
    landing = ROOT.joinpath("src/frontend/templates/site/index.html").read_text(encoding="utf-8")
    header = ROOT.joinpath("src/frontend/templates/site/includes/header.html").read_text(encoding="utf-8")

    assert 'href="/support"' in landing
    assert 'href="/support"' in header


def test_support_copy_does_not_use_obsolete_tester_application_flow() -> None:
    support = ROOT.joinpath("src/frontend/templates/site/support.html").read_text(encoding="utf-8")
    landing = ROOT.joinpath("src/frontend/templates/site/index.html").read_text(encoding="utf-8")

    assert "Подать заявку" not in support
    assert "Статус заявки" not in support
    assert "закрытый канал" not in support
    assert "Подать заявку" not in landing
    assert "набор тестеров" not in landing


def test_support_hero_uses_functional_copy_without_duplicate_master_text() -> None:
    support = ROOT.joinpath("src/frontend/templates/site/support.html").read_text(encoding="utf-8")

    assert "Выберите раздел, ответьте на короткие вопросы" in support
    assert "Мастер ниже помогает" not in support
    assert "Это отдельная часть сайта" not in support


def test_support_css_keeps_header_cta_and_title_readable() -> None:
    css = ROOT.joinpath("src/frontend/static/css/site/pages/support.css").read_text(encoding="utf-8")
    header_css = ROOT.joinpath("src/frontend/static/css/site/shell/header.css").read_text(encoding="utf-8")
    landing_css = ROOT.joinpath("src/frontend/static/css/site/pages/the_sealed_world_landing.css").read_text(
        encoding="utf-8"
    )

    assert "background: rgba(5, 5, 7, 0.88);" in header_css
    assert ".page-the-sealed-world .site-header:not(.is-scrolled):not(.is-open)" in landing_css
    assert ".page-support .site-header:not(.is-scrolled):not(.is-open)" not in css
    assert ".support-hero-actions .btn-node:first-child" in css
    assert "background: var(--col-accent);" in css
    assert ".support-copy h1" in css
    assert "line-height: 1.1;" in css

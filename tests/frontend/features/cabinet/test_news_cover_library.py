from pathlib import Path

from src.frontend.features.cabinet.modules.news_management.cover_library import get_news_cover_presets

ROOT = Path(__file__).resolve().parents[4]


def test_news_cover_library_exposes_static_synch_presets() -> None:
    presets = get_news_cover_presets()

    assert len(presets) == 13
    assert presets[0].key == "patch_delivered"
    assert presets[0].url == "/static/images/site/the-sealed-world/news-covers/patch-delivered.webp"
    assert presets[0].available is True
    assert any(p.key == "sync_error" for p in presets)
    assert any(p.key == "devblog_cute" for p in presets)
    assert any(p.key == "referral_invite" and p.available for p in presets)


def test_article_form_uses_cover_picker_instead_of_generation_flow() -> None:
    template = ROOT.joinpath("src/fastapi_cabinet/templates/cabinet/article_form.html").read_text(encoding="utf-8")

    assert "fc-cover-picker" in template
    assert "form.cover_presets" in template
    assert "/admin/news/generate-cover" not in template
    assert "/admin/news/approve-cover" not in template
    assert "Сгенерировать обложку" not in template

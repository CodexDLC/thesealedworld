from __future__ import annotations

from src.frontend.features.cabinet.modules.news_management.cover_workflow import (
    NewsCoverPromptInput,
    build_news_cover_prompt,
    extract_body_excerpt,
)


def test_news_cover_prompt_uses_article_content_without_html_tags() -> None:
    prompt = build_news_cover_prompt(
        NewsCoverPromptInput(
            title="Patch 0.2",
            preview="New monsters",
            body="<p>Added <strong>goblin</strong> clans.</p>",
            slug="patch-0-2",
            is_published=False,
        )
    )

    assert "Patch 0.2" in prompt
    assert "New monsters" in prompt
    assert "Added goblin clans." in prompt
    assert "<strong>" not in prompt
    assert "no text" in prompt


def test_news_cover_excerpt_is_compact_and_bounded() -> None:
    excerpt = extract_body_excerpt("<p>" + ("word " * 1000) + "</p>", max_chars=32)

    assert len(excerpt) <= 32
    assert excerpt.endswith("…")

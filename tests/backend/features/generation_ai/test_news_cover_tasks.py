from __future__ import annotations

import pytest

from src.backend.features.generation_ai.tasks_news import (
    NEWS_COVER_IMAGE_TASK,
    NewsCoverImageTaskHandler,
    build_news_cover_image_task_spec,
    normalize_news_cover_slug,
)


class FakeTask:
    input_payload: dict

    def __init__(self, payload: dict) -> None:
        self.input_payload = payload


@pytest.mark.unit
def test_news_cover_task_spec_uses_stable_slug_namespace() -> None:
    spec = build_news_cover_image_task_spec(
        article_id="42",
        slug="Launch Update",
        title="Launch",
        preview="Preview",
        body_excerpt="Body",
        prompt="Create cover",
    )

    assert spec.task_type == NEWS_COVER_IMAGE_TASK
    assert spec.entity_type == "news_article"
    assert spec.entity_id == "42"
    assert spec.output_kind == "image"
    assert spec.input_payload["storage_key"].startswith("news/covers/launch-update/")
    assert spec.input_payload["storage_key"].endswith(".webp")
    assert spec.metadata["storage_key"] == spec.input_payload["storage_key"]


@pytest.mark.unit
def test_news_cover_slug_normalization_rejects_empty_slug() -> None:
    assert normalize_news_cover_slug("Patch 0.2!") == "patch-0-2"
    with pytest.raises(ValueError):
        normalize_news_cover_slug("!!!")


@pytest.mark.unit
async def test_news_cover_handler_builds_image_request() -> None:
    task = FakeTask(
        {
            "prompt": "Create cover",
            "storage_key": "news/covers/launch/hash.webp",
            "content_type": "image/webp",
            "model": "gemini-2.5-flash-image",
        }
    )

    request = await NewsCoverImageTaskHandler().build_request(task)

    assert request["kind"] == "image"
    assert request["prompt"].startswith("Create cover")
    assert "No visible text" in request["prompt"]
    assert request["model"] == "gemini-2.5-flash-image"
    assert request["content_type"] == "image/webp"
    assert request["storage_key"] == "news/covers/launch/hash.webp"

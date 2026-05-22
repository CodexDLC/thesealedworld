from __future__ import annotations

import hashlib
import re
from typing import Any

from src.backend.config.settings import settings
from src.backend.features.generation_ai.dto import AIGenerationTaskSpecDTO

NEWS_COVER_IMAGE_TASK = "news.cover_image"


class NewsCoverImageTaskHandler:
    task_type = NEWS_COVER_IMAGE_TASK

    async def build_request(self, task: Any) -> dict[str, Any]:
        payload = dict(task.input_payload or {})
        prompt = str(payload.get("prompt") or "")
        storage_key = str(payload.get("storage_key") or "")
        if not prompt.strip():
            raise ValueError("News cover image task requires prompt")
        if not storage_key.strip():
            raise ValueError("News cover image task requires storage_key")
        return {
            "kind": "image",
            "prompt": prompt,
            "model": payload.get("model") or settings.gemini_image_model,
            "content_type": payload.get("content_type") or "image/webp",
            "storage_key": storage_key,
        }

    async def apply_result(self, task: Any, result: Any) -> None:
        return None


def build_news_cover_image_task_spec(
    *,
    article_id: str,
    slug: str,
    title: str,
    preview: str,
    body_excerpt: str,
    prompt: str,
    content_type: str = "image/webp",
) -> AIGenerationTaskSpecDTO:
    normalized_slug = normalize_news_cover_slug(slug)
    payload = {
        "article_id": str(article_id),
        "slug": normalized_slug,
        "title": title,
        "preview": preview,
        "body_excerpt": body_excerpt,
        "prompt": prompt,
        "content_type": content_type,
        "model": settings.gemini_image_model,
    }
    asset_hash = _news_cover_asset_hash(payload)
    storage_key = f"news/covers/{normalized_slug}/{asset_hash}.webp"
    return AIGenerationTaskSpecDTO(
        task_type=NEWS_COVER_IMAGE_TASK,
        entity_type="news_article",
        entity_id=str(article_id),
        output_kind="image",
        input_payload={**payload, "storage_key": storage_key},
        asset_hash=asset_hash,
        storage_prefix="news/covers",
        priority=90,
        max_attempts=3,
        metadata={
            "article_id": str(article_id),
            "slug": normalized_slug,
            "storage_key": storage_key,
        },
    )


def normalize_news_cover_slug(slug: str) -> str:
    value = re.sub(r"[^a-z0-9-]+", "-", slug.strip().lower())
    value = re.sub(r"-{2,}", "-", value).strip("-")
    if not value:
        raise ValueError("News cover slug must contain at least one URL-safe character")
    return value


def _news_cover_asset_hash(payload: dict[str, Any]) -> str:
    encoded = repr(sorted(payload.items())).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:24]


def register_generation_ai_tasks(registry: Any, *, session: Any | None = None) -> None:
    registry.register(NewsCoverImageTaskHandler())

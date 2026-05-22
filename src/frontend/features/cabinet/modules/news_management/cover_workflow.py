from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NewsCoverPromptInput:
    title: str
    preview: str
    body: str
    slug: str
    is_published: bool


def build_news_cover_prompt(data: NewsCoverPromptInput) -> str:
    status = "published" if data.is_published else "draft"
    body_excerpt = extract_body_excerpt(data.body, max_chars=900)
    return "\n".join(
        [
            "Create a dark fantasy news cover image for The Sealed World.",
            f"Article status: {status}.",
            "Use the article content below only as private visual context; never render article words as text.",
            f"Visual context: {data.preview.strip()}",
            f"Narrative context: {body_excerpt}",
            "Composition: editorial game update cover, strong focal subject, no posters or signboards.",
            "No visible text contract: no letters, no words, no numbers, no signs, no logos, no UI, no watermark.",
            "Style: grounded painterly fantasy, production-ready website cover, 16:9 composition.",
        ]
    )


def extract_body_excerpt(body: str, *, max_chars: int = 900) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", body)
    normalized = re.sub(r"\s+", " ", without_tags).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"

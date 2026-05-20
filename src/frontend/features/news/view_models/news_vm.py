from __future__ import annotations

import math
from dataclasses import dataclass, field

from src.frontend.features.news.services.news_service import ARTICLES_PER_PAGE


@dataclass(frozen=True)
class ArticleCardVM:
    slug: str
    title: str
    preview: str
    published_at: str
    cover_image: str | None = None


@dataclass(frozen=True)
class NewsListVM:
    articles: list[ArticleCardVM] = field(default_factory=list)
    page: int = 1
    total: int = 0
    empty_message: str = "Новостей пока нет. Следите за обновлениями."

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(self.total / ARTICLES_PER_PAGE))

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


@dataclass(frozen=True)
class ArticleDetailVM:
    slug: str
    title: str
    body: str
    published_at: str
    cover_image: str | None = None

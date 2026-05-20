from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.frontend.features.news.models.article import Article
    from src.frontend.features.news.repositories.article_repository import ArticleRepository

ARTICLES_PER_PAGE = 10


class NewsService:
    def __init__(self, repo: ArticleRepository) -> None:
        self._repo = repo

    async def list_published(self, *, page: int = 1) -> tuple[list[Article], int]:
        offset = (max(page, 1) - 1) * ARTICLES_PER_PAGE
        articles = await self._repo.get_published(limit=ARTICLES_PER_PAGE, offset=offset)
        total = await self._repo.count_published()
        return articles, total

    async def get_article(self, slug: str) -> Article | None:
        return await self._repo.get_by_slug(slug)

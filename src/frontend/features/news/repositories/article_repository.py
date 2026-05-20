from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from src.frontend.features.news.models.article import Article

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ArticleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_published(self, *, limit: int = 20, offset: int = 0) -> list[Article]:
        stmt = (
            select(Article)
            .where(Article.is_published.is_(True))
            .order_by(Article.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_published(self) -> int:
        stmt = select(func.count()).select_from(Article).where(Article.is_published.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_slug(self, slug: str) -> Article | None:
        stmt = select(Article).where(Article.slug == slug, Article.is_published.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

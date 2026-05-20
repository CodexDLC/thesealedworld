from __future__ import annotations

from datetime import UTC, datetime
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

    # ── Admin methods ────────────────────────────────────────────────────────

    async def get_all(self, *, limit: int = 50, offset: int = 0) -> list[Article]:
        stmt = select(Article).order_by(Article.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        stmt = select(func.count()).select_from(Article)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_drafts(self) -> int:
        stmt = select(func.count()).select_from(Article).where(Article.is_published.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_drafts(self, *, limit: int = 50, offset: int = 0) -> list[Article]:
        stmt = (
            select(Article)
            .where(Article.is_published.is_(False))
            .order_by(Article.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, article_id: int) -> Article | None:
        stmt = select(Article).where(Article.id == article_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, *, slug: str, title: str, preview: str, body: str, cover_image: str | None = None
    ) -> Article:
        article = Article(slug=slug, title=title, preview=preview, body=body, cover_image=cover_image)
        self.session.add(article)
        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def update(
        self,
        article: Article,
        *,
        slug: str,
        title: str,
        preview: str,
        body: str,
        cover_image: str | None = None,
    ) -> Article:
        article.slug = slug
        article.title = title
        article.preview = preview
        article.body = body
        article.cover_image = cover_image
        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def toggle_publish(self, article: Article) -> Article:
        if article.is_published:
            article.is_published = False
            article.published_at = None
        else:
            article.is_published = True
            article.published_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def delete(self, article: Article) -> None:
        await self.session.delete(article)
        await self.session.commit()

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
            event_type = "news.unpublished"
        else:
            article.is_published = True
            article.published_at = datetime.now(UTC)
            event_type = "news.published"
        await self.session.commit()
        await self.session.refresh(article)

        await self._publish_news_event(article, event_type=event_type)

        return article

    async def _publish_news_event(self, article: Article, *, event_type: str) -> None:
        try:
            import os

            import redis.asyncio as redis
            from codex_platform.streams.producer import StreamProducer

            from src.frontend.config.settings import settings

            redis_url = os.getenv("REDIS_URL") or getattr(settings, "redis_url", "redis://localhost:6379/0")
            redis_client = redis.from_url(redis_url, decode_responses=True)
            stream_name = getattr(settings, "game_stream_name", "game_events")

            producer = StreamProducer(redis_client, stream_name)
            event_data = {
                "id": str(article.id),
                "title": article.title,
                "slug": article.slug,
                "preview": article.preview or "",
                "cover_image": article.cover_image or "",
            }
            await producer.publish(event_type, event_data)
            await redis_client.aclose()
        except Exception as e:
            from loguru import logger

            logger.opt(exception=True).error(f"Failed to publish {event_type} event to Redis Stream: {e}")

    async def delete(self, article: Article) -> None:
        await self.session.delete(article)
        await self.session.commit()

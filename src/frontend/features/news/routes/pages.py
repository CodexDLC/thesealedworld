from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.frontend.core.database import get_db
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.news.repositories.article_repository import ArticleRepository
from src.frontend.features.news.services.news_service import NewsService
from src.frontend.features.news.view_models.news_vm import ArticleCardVM, ArticleDetailVM, NewsListVM

router = APIRouter(tags=["News"])


@router.get("/news", name="news")
async def news_list(
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    page: int = Query(1, ge=1),
):
    repo = ArticleRepository(session=db)
    service = NewsService(repo=repo)
    articles, total = await service.list_published(page=page)

    vm = NewsListVM(
        articles=[
            ArticleCardVM(
                slug=a.slug,
                title=a.title,
                preview=a.preview,
                published_at=a.published_at.strftime("%d.%m.%Y") if a.published_at else "",
                cover_image=a.cover_image,
            )
            for a in articles
        ],
        page=page,
        total=total,
    )
    return await ui.render(
        "site/news/list.html",
        context={
            "news": vm,
            "meta": {
                "title": "Новости - The Sealed World",
                "description": "Новости разработки, альфа-патчи и заметки мира The Sealed World.",
                "url": "/news",
            },
        },
    )


@router.get("/news/{slug}", name="news_detail")
async def news_detail(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    repo = ArticleRepository(session=db)
    service = NewsService(repo=repo)
    article = await service.get_article(slug)

    if article is None:
        return RedirectResponse(url="/news", status_code=303)

    vm = ArticleDetailVM(
        slug=article.slug,
        title=article.title,
        preview=article.preview,
        body=article.body,
        published_at=article.published_at.strftime("%d.%m.%Y") if article.published_at else "",
        cover_image=article.cover_image,
    )
    return await ui.render(
        "site/news/detail.html",
        context={
            "article": vm,
            "meta": {
                "title": f"{article.title} - The Sealed World",
                "description": article.preview,
                "image": article.cover_image or "/static/images/site/the-sealed-world/hero-main.webp",
                "type": "article",
                "url": f"/news/{article.slug}",
            },
        },
    )

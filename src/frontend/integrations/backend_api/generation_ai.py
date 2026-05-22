from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.frontend.core.api import BaseApiClient


@dataclass(frozen=True)
class GenerationTaskView:
    task_id: str
    task_type: str
    entity_type: str
    entity_id: str
    status: str
    storage_key: str = ""
    generated_url: str = ""
    error: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenerationTaskView:
        return cls(
            task_id=str(data["task_id"]),
            task_type=str(data.get("task_type") or ""),
            entity_type=str(data.get("entity_type") or ""),
            entity_id=str(data.get("entity_id") or ""),
            status=str(data.get("status") or ""),
            storage_key=str(data.get("storage_key") or ""),
            generated_url=str(data.get("generated_url") or ""),
            error=dict(data.get("error") or {}),
        )


@dataclass(frozen=True)
class GenerationTaskCreateResult:
    task_id: str
    status: str
    created: bool
    scheduled: int
    storage_key: str = ""
    generated_url: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenerationTaskCreateResult:
        return cls(
            task_id=str(data["task_id"]),
            status=str(data.get("status") or ""),
            created=bool(data.get("created")),
            scheduled=int(data.get("scheduled") or 0),
            storage_key=str(data.get("storage_key") or ""),
            generated_url=str(data.get("generated_url") or ""),
        )


class GenerationAIAdminApi(BaseApiClient):
    async def request_news_cover(
        self,
        *,
        article_id: str,
        slug: str,
        title: str,
        preview: str,
        body_excerpt: str,
        prompt: str,
    ) -> GenerationTaskCreateResult:
        raw = await self._request(
            "POST",
            "/api/admin/generation-ai/news-covers",
            json={
                "article_id": article_id,
                "slug": slug,
                "title": title,
                "preview": preview,
                "body_excerpt": body_excerpt,
                "prompt": prompt,
            },
        )
        return GenerationTaskCreateResult.from_dict(dict(raw or {}))

    async def get_task(self, task_id: str) -> GenerationTaskView:
        raw = await self._request("GET", f"/api/admin/generation-ai/tasks/{task_id}")
        return GenerationTaskView.from_dict(dict(raw or {}))

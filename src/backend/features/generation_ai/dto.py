from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

AIGenerationOutputKind = Literal["text", "image", "audio", "video", "json"]
AIGenerationTaskStatus = Literal["pending", "running", "cooldown", "done", "failed", "cancelled"]


class AIGenerationTaskSpecDTO(BaseModel):
    task_type: str
    entity_type: str
    entity_id: str
    output_kind: AIGenerationOutputKind
    prompt_payload: dict[str, Any] = Field(default_factory=dict)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    season_id: str | None = None
    asset_hash: str | None = None
    model: str | None = None
    priority: int = Field(default=100, ge=0)
    max_attempts: int = Field(default=3, ge=1, le=20)
    storage_prefix: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_task_identity(self) -> AIGenerationTaskSpecDTO:
        for field_name in ("task_type", "entity_type", "entity_id"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")
        return self


class AIGenerationTaskResultDTO(BaseModel):
    output_payload: dict[str, Any] = Field(default_factory=dict)
    storage_key: str | None = None
    generated_url: str | None = None
    asset_hash: str | None = None
    storage_backend: str | None = None
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIGenerationEnqueueResultDTO(BaseModel):
    batch_id: str
    task_ids: list[str] = Field(default_factory=list)
    created: int = 0
    reused: int = 0
    scheduled: int = 0


class AIGenerationTaskViewDTO(BaseModel):
    task_id: str
    task_type: str
    entity_type: str
    entity_id: str
    output_kind: AIGenerationOutputKind
    status: AIGenerationTaskStatus
    storage_key: str | None = None
    generated_url: str | None = None
    asset_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] = Field(default_factory=dict)


class AIGenerationTaskCreateResponseDTO(BaseModel):
    task_id: str
    status: AIGenerationTaskStatus
    created: bool
    scheduled: int = 0
    storage_key: str | None = None
    generated_url: str | None = None


class NewsCoverGenerationRequestDTO(BaseModel):
    article_id: str
    slug: str
    title: str
    preview: str = ""
    body_excerpt: str = ""
    prompt: str
    content_type: str = "image/webp"

    @model_validator(mode="after")
    def validate_news_cover_request(self) -> NewsCoverGenerationRequestDTO:
        if not self.article_id.strip():
            raise ValueError("article_id must not be empty")
        if not self.slug.strip():
            raise ValueError("slug must not be empty")
        if not self.prompt.strip():
            raise ValueError("prompt must not be empty")
        return self

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FeedbackItemState:
    id: str
    email: str
    type: str
    title: str
    body: str
    status: str
    priority: str | None
    created_at: str
    status_url: str = ""


@dataclass
class FeedbackListState:
    rows: list[FeedbackItemState] = field(default_factory=list)
    total_count: int = 0
    new_count: int = 0
    empty_message: str = "Фидбек отсутствует"

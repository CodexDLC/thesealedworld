from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FeedbackItemVM:
    id: int
    type: str
    title: str
    status: str
    created_at: str
    priority: str | None = None


@dataclass(frozen=True)
class FeedbackListVM:
    items: list[FeedbackItemVM] = field(default_factory=list)
    empty_message: str = "Вы ещё не отправляли фидбек"


@dataclass(frozen=True)
class FeedbackFormVM:
    types: list[tuple[str, str]] = field(
        default_factory=lambda: [
            ("bug", "Баг"),
            ("wish", "Пожелание"),
            ("impression", "Впечатление"),
            ("balance", "Баланс"),
        ]
    )
    priorities: list[tuple[str, str]] = field(
        default_factory=lambda: [
            ("minor", "Незначительный"),
            ("blocking", "Блокирующий"),
            ("critical", "Критический"),
        ]
    )

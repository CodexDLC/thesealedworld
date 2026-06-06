from __future__ import annotations

from dataclasses import dataclass

from src.frontend.config.settings import settings

_PUBLIC_BASE = "/static/images/site/the-sealed-world/news-covers"
_STATIC_BASE = settings.static_dir / "images" / "site" / "the-sealed-world" / "news-covers"


@dataclass(frozen=True)
class NewsCoverPreset:
    key: str
    title: str
    description: str
    filename: str

    @property
    def url(self) -> str:
        return f"{_PUBLIC_BASE}/{self.filename}"

    @property
    def available(self) -> bool:
        return (_STATIC_BASE / self.filename).exists()


NEWS_COVER_PRESETS: tuple[NewsCoverPreset, ...] = (
    NewsCoverPreset(
        key="patch_delivered",
        title="Патчноут доставлен",
        description="Синх приносит свиток обновления из Разлома.",
        filename="patch-delivered.webp",
    ),
    NewsCoverPreset(
        key="update_ready",
        title="Обновление готово",
        description="Радостный Синх и эфирные вспышки вокруг релиза.",
        filename="update-ready.webp",
    ),
    NewsCoverPreset(
        key="maintenance",
        title="Технические работы",
        description="Синх чинит эфирную сферу у обломка Монолита.",
        filename="maintenance.webp",
    ),
    NewsCoverPreset(
        key="sync_error",
        title="Ошибка синхронизации",
        description="Тревожный Синх и красные аварийные AR-глифы.",
        filename="sync-error.webp",
    ),
    NewsCoverPreset(
        key="new_zone",
        title="Новая зона открыта",
        description="Синх указывает на новый Разлом или маршрут.",
        filename="new-zone.webp",
    ),
    NewsCoverPreset(
        key="community_contest",
        title="Конкурс сообщества",
        description="Синх вручает эфирную статуэтку победителям.",
        filename="community-contest.webp",
    ),
    NewsCoverPreset(
        key="settler_recruitment",
        title="Набор в Поселенцы",
        description="Синх машет у ворот Цитадели D4.",
        filename="settler-recruitment.webp",
    ),
    NewsCoverPreset(
        key="rift_event",
        title="Ивент в Разломе",
        description="Синх бежит в Разлом с AR-индикаторами события.",
        filename="rift-event.webp",
    ),
    NewsCoverPreset(
        key="important_announcement",
        title="Важное объявление",
        description="Синх в строгой позе перед сигнальными панелями.",
        filename="important-announcement.webp",
    ),
    NewsCoverPreset(
        key="devblog_cute",
        title="Девблог / милота",
        description="Синх спит в Хабе под мягким эфирным полем.",
        filename="devblog-cute.webp",
    ),
    NewsCoverPreset(
        key="balance_update",
        title="Баланс и бой",
        description="Синх изучает боевые схемы и размены намерений.",
        filename="balance-update.webp",
    ),
    NewsCoverPreset(
        key="content_ops",
        title="Контент и монстры",
        description="Синх инспектирует карточки существ и трофеев.",
        filename="content-ops.webp",
    ),
    NewsCoverPreset(
        key="referral_invite",
        title="Реферальное приглашение",
        description="Синх передает эфирный кристалл приглашения.",
        filename="referral-invite.webp",
    ),
)


def get_news_cover_presets() -> tuple[NewsCoverPreset, ...]:
    return NEWS_COVER_PRESETS

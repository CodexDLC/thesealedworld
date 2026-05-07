from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime as dt


@dataclass(frozen=True, slots=True)
class SeasonDTO:
    id: int
    name: str
    started_at: dt.datetime
    ends_at: dt.datetime
    status: str
    reward_pool_total: int

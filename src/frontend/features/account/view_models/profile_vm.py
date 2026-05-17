from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccountProfileVM:
    email: str
    created_at: str
    tester_status: str
    tester_approved_at: str | None
    is_tester: bool
    can_create_character: bool

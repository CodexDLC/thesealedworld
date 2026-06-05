from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccountProfileVM:
    account_id: str
    email: str
    created_at: str
    display_name: str
    initials: str
    referral_code: str
    referral_link: str
    referrals_invited: int
    referrals_active: int
    referral_bonus: int
    tester_status: str
    tester_approved_at: str | None
    is_tester: bool
    can_create_character: bool

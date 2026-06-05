import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.frontend.core.database import Base


class ReferralReward(Base):
    __tablename__ = "auth_referral_rewards"
    __table_args__ = (
        UniqueConstraint("referrer_id", "referee_id", "kind", name="uq_auth_referral_rewards_event"),
        {"schema": "site"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    referrer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("site.auth_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("site.auth_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

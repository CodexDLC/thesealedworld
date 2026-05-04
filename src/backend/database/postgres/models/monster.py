import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database.postgres.models.base import Base


class GeneratedClanORM(Base):
    __tablename__ = "generated_clans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    family_id: Mapped[str] = mapped_column(String, nullable=False)  # "orcs_family"
    tier: Mapped[int] = mapped_column(Integer, nullable=False)  # 2

    # --- ПРИВЯЗКА К МИРУ ---
    zone_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # --- НОВЫЕ ПОЛЯ ХЭШЕЙ ---
    context_hash: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    unique_hash: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)

    # --- ОСТАЛЬНОЕ ---
    raw_tags: Mapped[dict] = mapped_column(JSON, nullable=False)
    flavor_content: Mapped[dict] = mapped_column(JSON, nullable=False)

    name_ru: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    members: Mapped[list["GeneratedMonsterORM"]] = relationship(
        "GeneratedMonsterORM", back_populates="clan", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (Index("ix_clan_context_lookup", "context_hash", "tier"),)


class GeneratedMonsterORM(Base):
    """
    Таблица СГЕНЕРИРОВАННЫХ МОНСТРОВ (Инстансы).
    """

    __tablename__ = "generated_monsters"

    # --- ID и Связи ---
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    clan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generated_clans.id", ondelete="CASCADE"), nullable=False, index=True
    )

    clan: Mapped["GeneratedClanORM"] = relationship("GeneratedClanORM", back_populates="members")

    # --- БАЛАНС И ИДЕНТИФИКАЦИЯ ---
    variant_key: Mapped[str] = mapped_column(String, nullable=False)

    role: Mapped[str] = mapped_column(String, nullable=False)  # "minion", "elite", "boss"
    threat_rating: Mapped[int] = mapped_column(Integer, nullable=False)  # ex: 50

    # --- НАРРАТИВ ---
    name_ru: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    # --- SNAPSHOTS ---
    scaled_base_stats: Mapped[dict] = mapped_column(JSON, nullable=False)
    loadout_ids: Mapped[dict] = mapped_column(JSON, nullable=False)  # Обычно это список или dict
    skills_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)  # Обычно список
    current_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (Index("ix_monster_role_threat", "role", "threat_rating"),)

    def __repr__(self):
        return f"<Monster {self.name_ru} ({self.variant_key}) Threat:{self.threat_rating}>"

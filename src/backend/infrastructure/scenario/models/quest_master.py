from __future__ import annotations

from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, TimestampMixin


class ScenarioMaster(Base, TimestampMixin):
    __tablename__ = "scenario_master"

    quest_key: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, server_default="Unknown Quest")
    start_node_id: Mapped[str] = mapped_column(String(50), nullable=False)
    master_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status_bar_fields: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
